from typing import List, Tuple, Optional, Union, Dict
from datetime import datetime
import math
import os

from highway_env.road.road import Road, RoadNetwork, LaneIndex
from highway_env.road.lane import (
    StraightLane, CircularLane, SineLane, PolyLane, PolyLaneFixedWidth
)
from highway_env.envs.common.abstract import AbstractEnv
from highway_env.vehicle.controller import MDPVehicle
from highway_env.vehicle.behavior import IDMVehicle
import numpy as np

from dilu.scenario.DBBridge import DBBridge
from dilu.scenario.envPlotter import ScePlotter


ACTIONS_ALL = {
    0: 'LANE_LEFT',
    1: 'IDLE',
    2: 'LANE_RIGHT',
    3: 'FASTER',
    4: 'SLOWER'
}

ACTIONS_DESCRIPTION = {
    0: 'Turn-left - change lane to the left of the current lane',
    1: 'REMAIN - remain in the current lane with current speed',
    2: 'Turn-right - change lane to the right of the current lane',
    3: 'Acceleration - accelerate the car',
    4: 'Deceleration - decelerate the car'
}


class EnvScenario:
    def __init__(
            self, env: AbstractEnv, envType: str,
            seed: int, database: str = None
    ) -> None:
        self.env = env
        self.road: Road = env.road
        self.network: RoadNetwork = self.road.network
        self.previous_lanes_count = 2
        self.envType = envType
        self.is_merge_env = 'merge-v0' in envType.lower()
        self.is_roundabout_env = 'roundabout-v0' in envType.lower()  # 添加这行
        self.is_racetrack_env = 'racetrack-v0' in envType.lower()

        self.ego: MDPVehicle = env.vehicle
        # 下面的四个变量用来判断车辆是否在 ego 的危险视距内
        self.theta1 = math.atan(3/17.5)
        self.theta2 = math.atan(2/2.5)
        self.radius1 = np.linalg.norm([3, 17.5])
        self.radius2 = np.linalg.norm([2, 2.5])

        # 环岛特定参数
        self.center = [0, 0]
        self.radius = 20
        self.alpha = 24  # 度

        self.plotter = ScePlotter()
        if database:
            self.database = database
        else:
            self.database = datetime.strftime(
                datetime.now(), '%Y-%m-%d_%H-%M-%S'
            ) + '.db'

        if os.path.exists(self.database):
            os.remove(self.database)

        self.dbBridge = DBBridge(self.database, env)

        self.dbBridge.createTable()
        self.dbBridge.insertSimINFO(envType, seed)
        self.dbBridge.insertNetwork()

    def getSurrendVehicles(self, vehicles_count: int) -> object:
        return self.road.close_vehicles_to(
            self.ego, self.env.PERCEPTION_DISTANCE,
            count=vehicles_count-1, see_behind=True,
            sort='sorted'
        )

    def plotSce(self, fileName: str) -> None:
        SVs = self.getSurrendVehicles(10)
        self.plotter.plotSce(self.network, SVs, self.ego, fileName)

    def getUnitVector(self, radian: float) -> Tuple[float, float]:
        return (
            math.cos(radian), math.sin(radian)
        )

    def isInJunction(self, vehicle: Union[IDMVehicle, MDPVehicle]) -> float:
        if self.envType == 'intersection-v1':
            x, y = vehicle.position
            # 这里交叉口的范围是 -12~12, 这里是为了保证车辆可以检测到交叉口内部的信息
            # 这个时候车辆需要提前减速
            if -20 <= x <= 20 and -20 <= y <= 20:
                return True
            else:
                return False
        else:
            return False

    def is_on_roundabout(self, vehicle: Union[IDMVehicle, MDPVehicle]) -> bool:
        x, y = vehicle.position
        distance_from_center = math.sqrt((x - self.center[0]) ** 2 + (y - self.center[1]) ** 2)
        return self.radius - 2 <= distance_from_center <= self.radius + 6  # 考虑到内外两条车道

    def get_angle_on_roundabout(self, vehicle: Union[IDMVehicle, MDPVehicle]) -> float:
        x, y = vehicle.position
        angle = math.degrees(math.atan2(y - self.center[1], x - self.center[0])) % 360
        return angle

    def get_next_lane_racetrack(self, currentLaneIndex: LaneIndex) -> LaneIndex:
        # 根据 racetrack 环境的特点，自定义获取下一个车道的方法
        # 这里假设 racetrack 是一个闭环，下一条车道就是当前车道的下一个索引
        # 您需要根据实际的 racetrack 环境定义逻辑
        from_lane, to_lane, lane_id = currentLaneIndex
        # 简单示例：假设车道索引循环递增
        next_lane_id = (lane_id + 1) % len(self.network.graph[from_lane][to_lane])
        return (from_lane, to_lane, next_lane_id)

    def describe_roundabout(self) -> str:
        angle = self.get_angle_on_roundabout(self.ego)
        lane = self.network.get_closest_lane_index(self.ego.position)[2]
        description = f"You are driving on a roundabout. Your current position is at {angle:.2f} degrees. "
        description += f"You are on the {'inner' if lane == 0 else 'outer'} lane. "
        # 判断是否在入口或出口
        is_entry_exit, entry_exit_type = self.is_at_entry_or_exit(self.ego)
        if is_entry_exit:
            if entry_exit_type == "entry":
                description += "You are approaching the entry of the roundabout. Be prepared to yield to vehicles already in the roundabout. "
            else:  # exit
                description += "You are approaching an exit of the roundabout. If this is your intended exit, prepare to leave the roundabout. "
        description += f"Your coordinates are ({self.ego.position[0]:.2f}, {self.ego.position[1]:.2f}). "
        description += f"Your speed is {self.ego.speed:.2f} m/s and acceleration is {self.ego.action['acceleration']:.2f} m/s^2. "
        return description

    def describe_racetrack(self) -> str:
        # 根据 racetrack 环境定义路况描述
        description = "You are driving on a racetrack. Maintain your speed and follow the track.\n"
        description += f"Your coordinates are ({self.ego.position[0]:.2f}, {self.ego.position[1]:.2f}). "
        description += f"Your speed is {self.ego.speed:.2f} m/s and acceleration is {self.ego.action['acceleration']:.2f} m/s^2.\n"
        return description

    def describe_surrounding_vehicles(self) -> str:
        surrounding_vehicles = self.road.vehicles
        description = "Surrounding vehicles:\n"

        for vehicle in surrounding_vehicles:
            if vehicle is self.ego:
                continue

            if self.is_on_roundabout(vehicle):
                angle = self.get_angle_on_roundabout(vehicle)
                relative_angle = (angle - self.get_angle_on_roundabout(self.ego) + 360) % 360
                position = "ahead of" if 0 <= relative_angle <= 180 else "behind"

                description += f"- Vehicle at {angle:.2f} degrees, {position} you. "
                is_entry_exit, entry_exit_type = self.is_at_entry_or_exit(vehicle)
                if is_entry_exit:
                    if entry_exit_type == "entry":
                        description += "It is approaching the entry of the roundabout. "
                    else:
                        description += "It is approaching the exit of the roundabout. "
            else:
                road_id = self.network.get_closest_lane_index(vehicle.position)[0]
                description += f"- Vehicle on {road_id} approaching the roundabout. "

            description += f"Its speed is {vehicle.speed:.2f} m/s. "
            description += f"Its coordinates are ({vehicle.position[0]:.2f}, {vehicle.position[1]:.2f}).\n"

        return description

    def getLanePosition(self, vehicle: Union[IDMVehicle, MDPVehicle]) -> float:
        currentLaneIdx = vehicle.lane_index
        currentLane = self.network.get_lane(currentLaneIdx)
        # if not isinstance(currentLane, StraightLane):
        #     raise ValueError(
        #         "The vehicle is in a junction, can't get lane position"
        #     )
        # else:
        #     currentLane = self.network.get_lane(vehicle.lane_index)
        #     return np.linalg.norm(vehicle.position - currentLane.start)
        if isinstance(currentLane, StraightLane):
            return currentLane.local_coordinates(vehicle.position)[0]
        elif isinstance(currentLane, CircularLane):
            lane_coord = currentLane.local_coordinates(vehicle.position)
            return currentLane.length * lane_coord[0]
        else:
            raise ValueError(f"Unknown lane type: {type(currentLane)}")


    def availableActionsDescription(self) -> str:
        avaliableActionDescription = 'Your available actions are: \n'
        availableActions = self.env.get_available_actions()
        for action in availableActions:
            avaliableActionDescription += ACTIONS_DESCRIPTION[action] + ' Action_id: ' + str(
                action) + '\n'
        if self.is_roundabout_env:
            avaliableActionDescription += '\nRemember:\n'
            avaliableActionDescription += '- Always yield to vehicles already in the roundabout.\n'
            avaliableActionDescription += '- Use the outer lane if you\'re planning to exit soon.\n'
            avaliableActionDescription += '- Use the inner lane for going further around the roundabout.\n'
            avaliableActionDescription += '- Signal before exiting the roundabout.\n'
        # if 1 in availableActions:
        #     avaliableActionDescription += 'You should check IDLE action as FIRST priority. '
        # if 0 in availableActions or 2 in availableActions:
        #     avaliableActionDescription += 'For change lane action, CAREFULLY CHECK the safety of vehicles on target lane. '
        # if 3 in availableActions:
        #     avaliableActionDescription += 'Consider acceleration action carefully. '
        # if 4 in availableActions:
        #     avaliableActionDescription += 'The deceleration action is LAST priority. '
        # avaliableActionDescription += '\n'
        return avaliableActionDescription

    def processNormalLane(self, lidx: LaneIndex) -> str:
        if self.is_merge_env:
            return self.processMergeLane(lidx)
        sideLanes = self.network.all_side_lanes(lidx)
        numLanes = len(sideLanes)
        if numLanes == 1:
            description = "You are driving on a road with only one lane, you can't change lane. "
        else:
            egoLaneRank = lidx[2]
            if egoLaneRank == 0:
                description = f"You are driving on a road with {numLanes} lanes, occupying the leftmost lane. "
            elif egoLaneRank == numLanes - 1:
                description = f"You are driving on a road with {numLanes} lanes, occupying the rightmost lane. "
            else:
                laneRankDict = {
                    1: 'second',
                    2: 'third',
                    3: 'fourth'
                }
                #description = f"You are driving on a road with {numLanes} lanes, and you are currently driving in the {laneRankDict[egoLaneRank]} lane from the left. "
                description = f"You are driving on a {numLanes}-lane highway, occupying the {laneRankDict[egoLaneRank]} lane from the left."

        description += f"You are located at coordinates `({self.ego.position[0]:.2f}, {self.ego.position[1]:.2f})`. Your vehicle is moving at {self.ego.speed:.2f} m/s with an acceleration of {self.ego.action['acceleration']:.2f} m/s^2. Your lateral position within the lane is {self.getLanePosition(self.ego):.2f} m.\n"
        #description += f"Your current position is `({self.ego.position[0]:.2f}, {self.ego.position[1]:.2f})`, speed is {self.ego.speed:.2f} m/s, acceleration is {self.ego.action['acceleration']:.2f} m/s^2, and lane position is {self.getLanePosition(self.ego):.2f} m.\n"
        return description

    def processMergeLane(self, lidx: LaneIndex) -> str:
        _from, _to, _id = lidx
        current_lane = self.network.get_lane(lidx)
        all_lanes = self.network.graph[_from][_to]

        description = ""

        # ego总是在主路上
        description += f"You are driving on the main road with {len(all_lanes)} lanes. "

        # 检查是否有合并车道
        if len(all_lanes) > 2:  # 假设初始状态有2条车道,多于2条时说明合并车道出现了
            if _id == len(all_lanes) - 2:  # ego在倒数第二条车道上
                description += "There is a merge lane to your right. Be cautious of merging vehicles. "
            elif _id == len(all_lanes) - 1:  # ego在最右侧车道上
                description += "You are in the rightmost lane. There is a merge lane to your right. Be prepared to allow vehicles to merge. "
            else:
                description += "There is a merge lane on the far right. "

        description += f"You are located at coordinates `({self.ego.position[0]:.2f}, {self.ego.position[1]:.2f})`. "
        description += f"Your vehicle is moving at {self.ego.speed:.2f} m/s with an acceleration of {self.ego.action['acceleration']:.2f} m/s^2. "

        # 获取车道上的位置
        long, lat = current_lane.local_coordinates(self.ego.position)
        description += f"Your longitudinal position within the lane is {long:.2f} m and lateral position is {lat:.2f} m.\n"

        return description

    # def is_at_entry_or_exit(self) -> Tuple[bool, str]:
    #     lane_id = self.network.get_closest_lane_index(self.ego.position)
    #     if lane_id[0].endswith('s') and lane_id[1].endswith('e'):  # 入口
    #         return True, "entry"
    #     elif lane_id[0].endswith('x') and lane_id[1].endswith('s'):  # 出口
    #         return True, "exit"
    #     return False, ""

    def get_next_lane(self, currentLaneIndex: LaneIndex) -> LaneIndex:
        if self.is_racetrack_env:
            return self.get_next_lane_racetrack(currentLaneIndex)
        elif hasattr(self.ego, 'route') and self.ego.route:
            return self.network.next_lane(currentLaneIndex, self.ego.route, self.ego.position)
        else:
            raise AttributeError("'Vehicle'对象没有'route'属性，且环境类型不支持获取nextLane。")

    def is_at_entry_or_exit(
            self, vehicle: Union[IDMVehicle, MDPVehicle]
    ) -> Tuple[bool, str]:
        lane_id = self.network.get_closest_lane_index(vehicle.position)
        from_lane, to_lane, _ = lane_id

        # 定义入口和出口车道的 from_lane 和 to_lane
        entry_lanes = {
            ('ser', 'ses'),
            ('ner', 'nes'),
            ('wer', 'wes'),
            ('wer', 'wes'),
            ('wxs', 'wxr'),
            ('nxs', 'nxr'),
            # 根据 RoundaboutEnv 的定义，添加更多入口车道
        }

        exit_lanes = {
            ('eer', 'ees'),
            ('exr', 'wxr'),
            ('ees', 'ee'),
            ('exs', 'exr'),
            # 根据 RoundaboutEnv 的定义，添加更多出口车道
        }

        if (from_lane, to_lane) in entry_lanes:
            return True, "entry"
        elif (from_lane, to_lane) in exit_lanes:
            return True, "exit"
        return False, ""

    def getSVRelativeState(self, sv: IDMVehicle) -> str:
        # CAUTION: 这里有一个问题，pygame 的 y 轴是上下颠倒的，向下是 y 轴的正方向。
        #       因此，在 highway-v0 上，车辆向左换道实际上是向右运动。因此判断车辆相
        #       对自车的位置，不能用向量来算，直接根据车辆在哪条车道上来判断是比较合适
        #       的，向量只能用来判断车辆在 ego 的前方还是后方
        relativePosition = sv.position - self.ego.position
        egoUnitVector = self.getUnitVector(self.ego.heading)
        cosineValue = sum(
            [x*y for x, y in zip(relativePosition, egoUnitVector)]
        )
        if cosineValue >= 0:
            return 'is ahead of you'
        else:
            return 'is behind of you'

    def getVehDis(self, veh: IDMVehicle):
        posA = self.ego.position
        posB = veh.position
        distance = np.linalg.norm(posA - posB)
        return distance

    def getClosestSV(self, SVs: List[IDMVehicle]):
        if SVs:
            closestIdex = -1
            closestDis = 99999999
            for i, sv in enumerate(SVs):
                dis = self.getVehDis(sv)
                if dis < closestDis:
                    closestDis = dis
                    closestIdex = i
            return SVs[closestIdex]
        else:
            return None

    def processSingleLaneSVs(self, SingleLaneSVs: List[IDMVehicle]):
        # 返回当前车道上，前方最近的车辆和后方最近的车辆，如果没有，则为 None
        if SingleLaneSVs:
            aheadSVs = []
            behindSVs = []
            for sv in SingleLaneSVs:
                RSStr = self.getSVRelativeState(sv)
                if RSStr == 'is ahead of you':
                    aheadSVs.append(sv)
                else:
                    behindSVs.append(sv)
            aheadClosestOne = self.getClosestSV(aheadSVs)
            behindClosestOne = self.getClosestSV(behindSVs)
            return aheadClosestOne, behindClosestOne
        else:
            return None, None

    def processSVsNormalLane(
            self, SVs: List[IDMVehicle], currentLaneIndex: LaneIndex
    ):
        try:
            nextLane = self.get_next_lane(currentLaneIndex)
        except AttributeError as e:
            print(f"获取nextLane时出错: {e}")
            nextLane = None  # 或者根据需求进行其他处理
        # 目前 description 中的车辆有些太多了，需要处理一下，只保留最靠近 ego 的几辆车
        classifiedSVs: Dict[str, List[IDMVehicle]] = {
            'current lane': [],
            'left lane': [],
            'right lane': [],
            'target lane': [],
            'merge lane':[]
        }
        sideLanes = self.network.all_side_lanes(currentLaneIndex)
        # nextLane = self.network.next_lane(
        #     currentLaneIndex, self.ego.route, self.ego.position
        # )
        for sv in SVs:
            lidx = sv.lane_index
            if lidx in sideLanes:
                if lidx == currentLaneIndex:
                    classifiedSVs['current lane'].append(sv)
                else:
                    laneRelative = lidx[2] - currentLaneIndex[2]
                    if laneRelative == 1:
                        classifiedSVs['right lane'].append(sv)
                    elif laneRelative == -1:
                        classifiedSVs['left lane'].append(sv)
                    else:
                        continue
            elif lidx == nextLane:
                classifiedSVs['target lane'].append(sv)
            else:
                continue
            if self.is_merge_env:
                # 特别关注最右侧车道(可能是合并车道)上的车辆
                rightmost_lane = max(sideLanes, key=lambda x: x[2])
                for sv in SVs:
                    if sv.lane_index == rightmost_lane:
                        classifiedSVs['merge lane'].append(sv)

        validVehicles: List[IDMVehicle] = []
        existVehicles: Dict[str, bool] = {}
        for k, v in classifiedSVs.items():
            if v:
                existVehicles[k] = True
            else:
                existVehicles[k] = False
            ahead, behind = self.processSingleLaneSVs(v)
            if ahead:
                validVehicles.append(ahead)
            if behind:
                validVehicles.append(behind)

        return validVehicles, existVehicles

    def describeSVNormalLane(self, currentLaneIndex: LaneIndex) -> str:
        # 当 ego 在 StraightLane 上时，车道信息是重要的，需要处理车道信息
        # 首先判断车辆是不是和车辆在同一条 road 上
        #   如果在同一条 road 上，则判断在哪条 lane 上
        #   如果不在同一条 road 上，则判断是否在 next_lane 上
        #      如果不在 nextLane 上，则直接不考虑这辆车的信息
        #      如果在 nextLane 上，则统计这辆车关于 ego 的相对运动状态
        # 检查 self.ego 是否具有 'route' 属性
        if hasattr(self.ego, 'route') and self.ego.route:
            nextLane = self.network.next_lane(
                currentLaneIndex, self.ego.route, self.ego.position
            )
        else:
            # 对于没有 'route' 属性的环境（如 racetrack），使用其他方法获取 nextLane
            nextLane = self.get_next_lane_racetrack(currentLaneIndex)

        sideLanes = self.network.all_side_lanes(currentLaneIndex)
        # nextLane = self.network.next_lane(
        #     currentLaneIndex, self.ego.route, self.ego.position
        # )
        surroundVehicles = self.getSurrendVehicles(10)

        validVehicles, existVehicles = self.processSVsNormalLane(
            surroundVehicles, currentLaneIndex
        )
        main_lanes_count = 2
        if not surroundVehicles:
            SVDescription = "There are no other vehicles driving near you, so you can drive completely according to your own ideas.\n"
            return SVDescription
        else:
            SVDescription = ''
            for sv in surroundVehicles:
                lidx = sv.lane_index
                if lidx in sideLanes:
                    # 车辆和 ego 在同一条 road 上行驶
                    if lidx == currentLaneIndex:
                        # 车辆和 ego 在同一条 lane 上行驶
                        if sv in validVehicles:
                            SVDescription += f"- Car `{id(sv) % 1000}` is driving on the same lane as you and {self.getSVRelativeState(sv)}. "
                        else:
                            continue
                    else:
                        laneRelative = lidx[2] - currentLaneIndex[2]
                        if laneRelative == 1:
                            # laneRelative = 1 表示车辆在 ego 的右侧车道上行驶
                            if sv in validVehicles:
                                if self.is_merge_env and currentLaneIndex[2] == main_lanes_count - 1 and lidx[2] == main_lanes_count:
                                    SVDescription += f"- Car `{id(sv) % 1000}` is merging from the right and {self.getSVRelativeState(sv)}. "
                                else:
                                    SVDescription += f"- Car `{id(sv) % 1000}` is driving on the lane to your right and {self.getSVRelativeState(sv)}. "
                            else:
                                continue
                        elif laneRelative == -1:
                            # laneRelative = -1 表示车辆在 ego 的左侧车道上行驶
                            if sv in validVehicles:
                                SVDescription += f"- Car `{id(sv) % 1000}` is driving on the lane to your left and {self.getSVRelativeState(sv)}. "
                            else:
                                continue
                        else:
                            # laneRelative 是其他的值表示在更远的车道上，不需要考虑
                            continue
                elif lidx == nextLane:
                    # 车辆在 ego 的 nextLane 上行驶
                    if sv in validVehicles:
                        SVDescription += f"- Car `{id(sv) % 1000}` is driving on your target lane and {self.getSVRelativeState(sv)}. "
                    else:
                        continue
                else:
                    continue
                if self.envType == 'intersection-v1':
                    SVDescription += f"The position of it is `({sv.position[0]:.2f}, {sv.position[1]:.2f})`, speed is {sv.speed:.2f} m/s, acceleration is {sv.action['acceleration']:.2f} m/s^2.\n"
                else:
                    SVDescription += f"The position of it is `({sv.position[0]:.2f}, {sv.position[1]:.2f})`, speed is {sv.speed:.2f} m/s, acceleration is {sv.action['acceleration']:.2f} m/s^2, and lane position is {self.getLanePosition(sv):.2f} m.\n"
            if SVDescription:
                descriptionPrefix = "Other vehicles are driving around you, and below is their basic information:\n"
                return descriptionPrefix + SVDescription
            else:
                SVDescription = 'No other vehicles driving near you, so you can drive completely according to your own ideas.\n'
                return SVDescription

    def isInDangerousArea(self, sv: IDMVehicle) -> bool:
        relativeVector = sv.position - self.ego.position
        distance = np.linalg.norm(relativeVector)
        egoUnitVector = self.getUnitVector(self.ego.heading)
        relativeUnitVector = relativeVector / distance
        alpha = np.arccos(
            np.clip(np.dot(egoUnitVector, relativeUnitVector), -1, 1)
        )
        if alpha <= self.theta1:
            if distance <= self.radius1:
                return True
            else:
                return False
        elif self.theta1 < alpha <= self.theta2:
            if distance <= self.radius2:
                return True
            else:
                return False
        else:
            return False

    def describeSVJunctionLane(self, currentLaneIndex: LaneIndex) -> str:
        # 当 ego 在交叉口内部时，车道的信息不再重要，只需要判断车辆和 ego 的相对位置
        # 但是需要判断交叉口内部所有车道关于 ego 的位置
        try:
            nextLane = self.get_next_lane(currentLaneIndex)
        except AttributeError as e:
            print(f"获取nextLane时出错: {e}")
            nextLane = None  # 或者根据需求进行其他处理
        # nextLane = self.network.next_lane(
        #     currentLaneIndex, self.ego.route, self.ego.position
        # )
        surroundVehicles = self.getSurrendVehicles(6)
        if not surroundVehicles:
            SVDescription = "There are no other vehicles driving near you, so you can drive completely according to your own ideas.\n"
            return SVDescription
        else:
            SVDescription = ''
            for sv in surroundVehicles:
                lidx = sv.lane_index
                if self.isInJunction(sv):
                    collisionPoint = self.getCollisionPoint(sv)
                    if collisionPoint:
                        SVDescription += f"- Car `{id(sv) % 1000}` is also in the junction and {self.getSVRelativeState(sv)}. The position of it is `({sv.position[0]:.2f}, {sv.position[1]:.2f})`, speed is {sv.speed:.2f} m/s, and acceleration is {sv.action['acceleration']:.2f} m/s^2. The potential collision point is `({collisionPoint[0]:.2f}, {collisionPoint[1]:.2f})`.\n"
                    else:
                        SVDescription += f"- Car `{id(sv) % 1000}` is also in the junction and {self.getSVRelativeState(sv)}. The position of it is `({sv.position[0]:.2f}, {sv.position[1]:.2f})`, speed is {sv.speed:.2f} m/s, and acceleration is {sv.action['acceleration']:.2f} m/s^2. You two are no potential collision.\n"
                elif lidx == nextLane:
                    collisionPoint = self.getCollisionPoint(sv)
                    if collisionPoint:
                        SVDescription += f"- Car `{id(sv) % 1000}` is driving on your target lane and {self.getSVRelativeState(sv)}. The position of it is `({sv.position[0]:.2f}, {sv.position[1]:.2f})`, speed is {sv.speed:.2f} m/s, and acceleration is {sv.action['acceleration']:.2f} m/s^2. The potential collision point is `({collisionPoint[0]:.2f}, {collisionPoint[1]:.2f})`.\n"
                    else:
                        SVDescription += f"- Car `{id(sv) % 1000}` is driving on your target lane and {self.getSVRelativeState(sv)}. The position of it is `({sv.position[0]:.2f}, {sv.position[1]:.2f})`, speed is {sv.speed:.2f} m/s, and acceleration is {sv.action['acceleration']:.2f} m/s^2. You two are no potential collision.\n"
                if self.isInDangerousArea(sv):
                    print(f"Vehicle {id(sv) % 1000} is in dangerous area.")
                    SVDescription += f"- Car `{id(sv) % 1000}` is also in the junction and {self.getSVRelativeState(sv)}. The position of it is `({sv.position[0]:.2f}, {sv.position[1]:.2f})`, speed is {sv.speed:.2f} m/s, and acceleration is {sv.action['acceleration']:.2f} m/s^2. This car is within your field of vision, and you need to pay attention to its status when making decisions.\n"
                else:
                    continue
            if SVDescription:
                descriptionPrefix = "Other vehicles are driving around you, and below is their basic information:\n"
                return descriptionPrefix + SVDescription
            else:
                'No other vehicles driving near you, so you can drive completely according to your own ideas.\n'
                return SVDescription

    def describe(self, decisionFrame: int) -> str:
        surroundVehicles = self.getSurrendVehicles(10)
        self.dbBridge.insertVehicle(decisionFrame, surroundVehicles)
        currentLaneIndex: LaneIndex = self.ego.lane_index
        if self.is_merge_env:
            roadCondition = self.processNormalLane(currentLaneIndex)
            SVDescription = self.describeSVNormalLane(currentLaneIndex)
        # if self.isInJunction(self.ego):
        #     roadCondition = "You are driving in an intersection, you can't change lane. "
        #     roadCondition += f"Your current position is `({self.ego.position[0]:.2f}, {self.ego.position[1]:.2f})`, speed is {self.ego.speed:.2f} m/s, and acceleration is {self.ego.action['acceleration']:.2f} m/s^2.\n"
        #     SVDescription = self.describeSVJunctionLane(currentLaneIndex)
        if self.is_roundabout_env:
            roadCondition = self.describe_roundabout()
            SVDescription = self.describe_surrounding_vehicles()
        if self.is_racetrack_env == 'racetrack-v0':
            roadCondition = self.describe_racetrack()
            SVDescription = self.describeSVNormalLane(currentLaneIndex)
        else:
            roadCondition = self.processNormalLane(currentLaneIndex)
            SVDescription = self.describeSVNormalLane(currentLaneIndex)

        return roadCondition + SVDescription

    def promptsCommit(
        self, decisionFrame: int, vectorID: str, done: bool,
        description: str, fewshots: str, thoughtsAndAction: str
    ):
        self.dbBridge.insertPrompts(
            decisionFrame, vectorID, done, description,
            fewshots, thoughtsAndAction
        )
