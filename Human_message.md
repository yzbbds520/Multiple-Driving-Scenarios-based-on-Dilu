This is the main query for the current timestep. It includes dynamically generated text describing the current environment.
Human Prompt Template
# Source: dilu/driver_agent/driverAgent.py

human_message = f"""
Above messages are some examples of how you successfully made decisions in the past. These scenarios are similar to the current one. Refer to those examples to make a decision for the current scenario.

current scenarios descriptions are attached as below:
{delimiter} Driving scenario description:
{scenario_description}
{delimiter} Available actions:
{available_actions}
{delimiter} Driving Intentions:
{driving_intentions}
"""
Use code with caution.
Python
Dynamic Content Generation
The placeholders {scenario_description} and {available_actions} are filled at runtime using methods from the EnvScenario class.
A. Generating scenario_description
This is created by EnvScenario.describe(). It combines a description of the ego vehicle's state with a summary of surrounding vehicles.
Ego Vehicle State (processNormalLane):
# Source: dilu/scenario/envScenario.py
# laneRankDict = {1: 'second', 2: 'third', 3: 'fourth'}
description = f"You are driving on a {numLanes}-lane highway, occupying the {laneRankDict[egoLaneRank]} lane from the left."
description += f"You are located at coordinates `({self.ego.position[0]:.2f}, {self.ego.position[1]:.2f})`. Your vehicle is moving at {self.ego.speed:.2f} m/s with an acceleration of {self.ego.action['acceleration']:.2f} m/s^2. Your lateral position within the lane is {self.getLanePosition(self.ego):.2f} m.\n"
Use code with caution.
Python
Surrounding Vehicles State (describeSVNormalLane):
The system identifies key vehicles (e.g., closest ahead/behind on adjacent lanes) and describes them relative to the ego vehicle.
# Source: dilu/scenario/envScenario.py
SVDescription = ""
# Example for a car on the same lane:
SVDescription += f"- Car `{id(sv) % 1000}` is driving on the same lane as you and {self.getSVRelativeState(sv)}. "
# Example for a car on the right lane:
SVDescription += f"- Car `{id(sv) % 1000}` is driving on the lane to your right and {self.getSVRelativeState(sv)}. "
# Common vehicle information:
SVDescription += f"The position of it is `({sv.position[0]:.2f}, {sv.position[1]:.2f})`, speed is {sv.speed:.2f} m/s, acceleration is {sv.action['acceleration']:.2f} m/s^2, and lane position is {self.getLanePosition(sv):.2f} m.\n"
Use code with caution.
Python
B. Generating available_actions
This is created by EnvScenario.availableActionsDescription() by iterating through the actions permitted by the environment at the current step.
# Source: dilu/scenario/envScenario.py

ACTIONS_DESCRIPTION = {
    0: 'Turn-left - change lane to the left of the current lane',
    1: 'REMAIN - remain in the current lane with current speed',
    2: 'Turn-right - change lane to the right of the current lane',
    3: 'Acceleration - accelerate the vehicle',
    4: 'Deceleration - decelerate the vehicle'
}


### 文件 2: `2_Reflection_Prompt.md`

```markdown
# Prompt for the Reflection Agent

This document outlines the prompt used by the Reflection Agent. The purpose of this agent is to analyze past failures (e.g., collisions), identify the root cause of the incorrect decision, and generate a corrected reasoning process. This corrected reasoning can then be added to the memory to prevent future mistakes.

**Note:** The exact implementation of `ReflectionAgent.py` was not provided, but its function can be inferred from its usage in `main.py`: `RA.reflection(docs[i]["human_question"], docs[i]["response"])`. The prompt below is a representative implementation based on this usage.

## Inferred Reflection Prompt

The agent is presented with the original scenario and the flawed response that led to a failure. It is tasked with acting as an expert critic to find the mistake and provide a better alternative.

```python
# This is a representative prompt inferred from the code's logic.

def generate_reflection_prompt(original_human_question: str, flawed_agent_response: str) -> str:
    """
    Generates a prompt for the reflection agent.

    Args:
        original_human_question: The full prompt given to the agent, including the scenario description.
        flawed_agent_response: The full response from the agent, including the reasoning that led to a failure.
    
    Returns:
        A string containing the reflection prompt.
    """
    
    delimiter = "####"
    
    reflection_prompt = f"""
You are an expert driving safety analyst. Your task is to review a decision made by an AI driver that resulted in a collision or an unsafe situation. You need to analyze the AI's reasoning, identify the mistake, and provide a corrected line of thought that would have led to a safe action.

{delimiter} **Original Scenario and Query** {delimiter}
Here is the situation the AI driver was facing:
{original_human_question}

{delimiter} **AI's Flawed Reasoning and Decision** {delimiter}
Here is the reasoning and the final action taken by the AI, which was incorrect:
{flawed_agent_response}

{delimiter} **Your Task** {delimiter}
1.  **Analyze the Error**: Pinpoint the specific error in the AI's reasoning. Did it misjudge a distance? Ignore a vehicle? Choose an aggressive action when a defensive one was needed?
2.  **Provide Corrected Reasoning**: Write a new, step-by-step reasoning process that correctly assesses the situation and prioritizes safety.
3.  **State the Correct Action**: Conclude with the correct action ID that should have been taken.

Your response must follow the same format as the original driver agent, ending with "Response to user:{delimiter} <Action_id>".

**Example Analysis:**
"The AI's reasoning was flawed because it decided to accelerate while the vehicle ahead was too close and braking. The AI failed to account for the negative relative speed. A safe driver would have recognized this hazard and chosen to decelerate to increase the following distance.

Corrected reasoning:
- The car ahead, `912`, is only 19.19m away and is 1.7 m/s slower. This is a critical situation.
- Accelerating or maintaining speed will lead to a collision.
- The only safe action is to decelerate immediately to create a larger safety buffer.
- Lane changing is not viable due to close traffic in adjacent lanes.
Final Answer: Deceleration

Response to user:{delimiter} 4"

Now, please perform your analysis on the provided case.
"""
    return reflection_prompt
Use code with caution.
---

文件 3: `3_Output_Correction_Prompt.md`

```markdown
# Prompt for the Output Format Correction Agent

This document describes a small, auxiliary prompt used for system robustness. If the main decision-making LLM fails to produce a valid integer action ID (e.g., it outputs text, or a number outside the valid range), this secondary agent is invoked to correct the format.

## Output Correction Prompt

This prompt is triggered within a `try-except` block in `DriverAgent.few_shot_decision`. It provides the malformed output to another LLM call with a very specific instruction: extract the correct integer.

```python
# Source: dilu/driver_agent/driverAgent.py

delimiter = "####"

# The `decision_action` variable holds the malformed output from the primary agent.
check_message = f"""
You are a output checking assistant who is responsible for checking the output of another agent.

The output you received is: {decision_action}

Your should just output the right int type of action_id, with no other characters or delimiters.
i.e. :
| Action_id | Action Description                                     |
|--------|--------------------------------------------------------|
| 0      | Turn-left: change lane to the left of the current lane |
| 1      | IDLE: remain in the current lane with current speed   |
| 2      | Turn-right: change lane to the right of the current lane|
| 3      | Acceleration: accelerate the vehicle                 |
| 4      | Deceleration: decelerate the vehicle                 |


You answer format would be:
{delimiter} <correct action_id within 0-4>
"""
