# Prompts for LLM-Driven Autonomous Driving Scenarios

We would like to express our sincere gratitude to Licheng Wen and the other authors of the Dilu project for generously open-sourcing their code. Our research builds upon their foundational work by expanding the scope to a broader range of driving scenarios. We hope that sharing these prompts will be beneficial to the research community.

For the specific implementation details of the agent and simulation loop, please refer to the original **[Dilu GitHub repository](https://github.com/georgewen2000/DiLU)**.

## Overview

This repository contains the structured prompts used in our research on LLM-driven autonomous driving. We are open-sourcing these materials to ensure the reproducibility of our experiments and to facilitate further research in this domain. The prompts are designed to be modular, allowing for dynamic construction based on real-time simulation data.

## Prompt Architecture

The final prompt sent to the Large Language Model (LLM) at each decision step is not a single static string. Instead, it is dynamically constructed by combining several key components in the following order:

1.  **System Prompt**: A static set of instructions that defines the AI's role, objectives, and required output format.
2.  **Few-Shot Examples/Experiences**: One or more examples of high-quality reasoning. These are crucial for guiding the model's thought process (Chain of Thought) and can be either standard successful cases or corrected past failures (experiences).
3.  **Human Message**: The actual query for the current timestep, containing a detailed description of the current driving scenario and available actions.

This modular approach allows the agent to leverage contextually relevant memories and adapt its reasoning based on the specific situation it faces.

## Repository Structure

Here is a description of the files contained in this repository:

-   `README.md`
    -   You are reading it. This file provides an overview and guide to the repository.

-   `System_Prompt.md`
    -   Contains the static system message that sets the core instructions for the LLM (e.g., "You are an AI Driver..."). This prompt is used at the beginning of every interaction.

-   `Human_message.md`
    -   Provides the template for the main query. During the simulation, this template is dynamically filled with real-time scenario descriptions and the set of available actions for the agent.

-   `Example_Answer.md`
    -   A canonical example of the desired reasoning process and final answer format from the LLM. This corresponds to a standard, successful driving decision and is used as a high-quality few-shot example.

-   `Few-Shot Examples.md`
    -   Contains the "human" or input part of standard few-shot examples, showcasing typical driving scenarios.

-   `Few-Shot-Experiences-Example.md`
    -   Contains more advanced few-shot examples derived from the agent's past **experiences**, specifically those that were corrected via the reflection mechanism. These are critical for teaching the agent to avoid repeating past mistakes and often include self-correction notes.

-   `Envscenario_of_5_Scenarios/`
    -   This directory contains the specific text-based scenario descriptions for the five distinct simulation environments used in our study. The content of these files is used to dynamically populate the `Human_message.md` template during runtime.

## How to Use

To reconstruct a complete prompt for a given scenario as used in our experiments:

1.  Start with the content from `System_Prompt.md`.
2.  Append one or more examples. For a standard case, combine the input from `Few-Shot Examples.md` with the output from `Example_Answer.md`. For a learning-from-mistake case, use the content from `Few-Shot-Experiences-Example.md`.
3.  Finally, take a scenario description from one of the files in the `Envscenario_of_5_Scenarios/` folder and insert it into the `Human_message.md` template. Append this to the prompt.

The resulting composite text forms the complete prompt that is sent to the LLM for a decision.

## Citation

If you find these prompts useful in your research, we would appreciate a citation to our paper.

```
[Your Paper Information Here, e.g., BibTeX entry]
```
