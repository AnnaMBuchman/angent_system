import randomname
import json
import random
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from group_agent import GroupAgentUtils
from collections import Counter


class LeaderAgentUtils:
    @staticmethod
    def create_leader_dict(name: str, friends: list, date: str, leader_meeting_hours: (int, int), leader_duration: int,
                           group_agent_name: str, regions: dict):

        if leader_meeting_hours[0] < 0 | leader_meeting_hours[0] > 23 | leader_meeting_hours[1] < 0 | \
                leader_meeting_hours[1] > 23:
            raise ValueError("Wrong open hours it should be from 0 to 23")
        if leader_meeting_hours[0] >= leader_meeting_hours[1] < 0:
            raise ValueError("Wrong open hours second value should be larger than first")

        return {
            "name": name,
            "friends": friends,
            "date": date,
            "leader_meeting_hours": leader_meeting_hours,
            "leader_duration": leader_duration,
            "group_agent_name": group_agent_name,
            "regions": regions
        }

    @staticmethod
    def create_random_leader_dict(friends, group_agent_name, regions: dict):
        my_friends = []
        my_regions = {}
        for friend in friends:
            if random.choice([True, False]):
                my_friends.append(friend)
        if len(my_friends) == 0:
            my_friends.append(friends[0])
        for key, value in regions.items():
            if random.choice([True, False]):
                my_regions[key] = value
        if len(my_regions) == 0:
            my_regions["Mokotow"] = regions["Mokotow"]
        date = "2022-05-" + str(random.randint(1, 31))
        meeting_hours = (random.randint(0, 17), random.randint(19, 23))
        duration = random.randint(1, 2)
        name = randomname.get_name(noun=('fish'))
        return LeaderAgentUtils.create_leader_dict(name, my_friends, date, meeting_hours, duration, group_agent_name,
                                                   regions)

    @staticmethod
    def create_random_leader_dict_with_specific_date(friends, group_agent_name, regions: dict, date="2022-05-7"):
        my_friends = []
        my_regions = {}
        for friend in friends:
            if random.choice([True, False]):
                my_friends.append(friend)
        if len(my_friends) == 0:
            my_friends.append(friends[0])
        for key, value in regions.items():
            if random.choice([True, False]):
                my_regions[key] = value
        if len(my_regions) == 0:
            my_regions["Mokotow"] = regions["Mokotow"]
        meeting_hours = (random.randint(0, 17), random.randint(19, 23))
        duration = random.randint(1, 2)
        name = randomname.get_name(noun=('fish'))
        return LeaderAgentUtils.create_leader_dict(name, my_friends, date, meeting_hours, duration, group_agent_name,
                                                   regions)


class LeaderAgent(Agent):
    def __init__(self, ip, _pass, leader_dict: dict):
        Agent.__init__(self, ip, _pass)
        self._leader_dict = leader_dict
        self.yes_users_dict = {}
        self.group_dict = {}

    def ask_friends(self):
        messages = []
        for friend in self._leader_dict["friends"]:
            msg = Message(to=friend)
            msg.set_metadata("message_type", "leader_invitation")
            for_user_dict = {"date": self._leader_dict["date"],
                             "leader_meeting_hours": self._leader_dict["leader_meeting_hours"],
                             "leader_duration": self._leader_dict["leader_duration"],
                             "regions": self._leader_dict["regions"]}
            message_body = json.dumps(for_user_dict)
            msg.body = message_body
            messages.append(msg)
        return messages

    def create_group(self):
        msg = Message(to=self._leader_dict["group_agent_name"])
        msg.set_metadata("message_type", "created_group")
        types = [value["place_type"] for value in self.yes_users_dict.values()]
        users_regions = [value["region"] for value in self.yes_users_dict.values()]
        place_types = [v[0] for v in Counter(types).most_common(3)]
        regions_most_comm = [v[0] for v in Counter(users_regions).most_common(3)]
        regions = []
        for reg in regions_most_comm:
            regions.append(self._leader_dict["regions"][reg])
        num = len(self.yes_users_dict.keys())
        group_dict = GroupAgentUtils.create_group_dict(place_types, num, self._leader_dict["date"],
                                                       self._leader_dict["leader_meeting_hours"],
                                                       self._leader_dict["leader_duration"], regions,
                                                       self._leader_dict["name"])
        message_body = json.dumps(group_dict)
        msg.body = message_body
        return msg

    class LeaderCommunicationBehaviour(CyclicBehaviour):
        async def on_start(self):
            self.count_users_no = 0
            self.count_users_yes = 0
            messages = self.agent.ask_friends()
            for msg in messages:
                await self.send(msg)

        async def run(self):
            msg = await self.receive(timeout=10)
            if msg:
                if msg.get_metadata("message_type") == "user_invitation_answer":
                    self.count_users_yes += 1
                    body = json.loads(msg.body)
                    self.agent.yes_users_dict[str(msg.sender)] = body
                    if self.count_users_no + self.count_users_yes == len(self.agent._leader_dict["friends"]):
                        print(f"yes users: {self.count_users_yes}, no users: {self.count_users_no}")
                        msg_group_agent = self.agent.create_group()
                        await self.send(msg_group_agent)

                elif msg.get_metadata("message_type") == "no_user":
                    self.count_users_no += 1
                    if self.count_users_no == len(self.agent._leader_dict["friends"]):
                        msg = Message(to=self.agent._leader_dict["group_agent_name"])
                        msg.set_metadata("message_type", "kill_yourself")
                        msg.body = "kill yourself"
                        await self.send(msg)
                        print(f"yes users: {self.count_users_yes}, no users: {self.count_users_no}")
                        print("I have no good friends")
                        await self.agent.stop()
                    elif self.count_users_no + self.count_users_yes == len(self.agent._leader_dict["friends"]):
                        print(f"yes users: {self.count_users_yes}, no users: {self.count_users_no}")
                        msg_group_agent = self.agent.create_group()
                        await self.send(msg_group_agent)
                elif msg.get_metadata("message_type") == "reservation_made":
                    print(f"Leader {self.agent._leader_dict['name']} received with content: {msg.body}")
                    print("I can happily die, my friends has place to go")
                    await self.agent.stop()
                elif msg.get_metadata("message_type") == "no_place_to_go":
                    print("Leader received with content: {}".format(msg.body))
                    print("I'm gonna kill myself, I hava no place to go with my friends")
                    await self.agent.stop()

        async def on_end(self):
            print(
                f"Goodbye word, last words from leader agent name: {self.agent._leader_dict['name']}, jid: {str(self.agent.jid)}")
            await self.agent.stop()

    async def setup(self):
        print(f"Leader starting name: {self._leader_dict['name']}, jid: {str(self.jid)}")
        cwfb = self.LeaderCommunicationBehaviour()
        self.add_behaviour(cwfb)
