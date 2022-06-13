from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from place_types import *
import json
import random
import datetime


class GroupAgentUtils:
    @staticmethod
    def create_group_dict(place_types: list, number_of_guests: int,
                          date: str, meeting_hours: (int, int), duration: int, region_agents_name: list):

        if meeting_hours[0] < 0 | meeting_hours[0] > 23 | meeting_hours[1] < 0 | meeting_hours[1] > 23:
            raise ValueError("Wrong open hours it should be from 0 to 23")
        if meeting_hours[0] >= meeting_hours[1] < 0:
            raise ValueError("Wrong open hours second value should be larger than first")

        return {
            "place_types": place_types,
            "date": date,
            "number_of_guests": number_of_guests,
            "meeting_hours": meeting_hours,
            "duration": duration,
            "region_agents_name": region_agents_name
        }

    @staticmethod
    def generate_random_group_dict(region_agents_name: list):
        place_list = [e.name for e in PlaceTypes]
        rand_idx = random.randrange(len(place_list))
        random_places = []
        for i in range(3):
            rand_idx = random.randrange(len(place_list))
            random_places.append(place_list[rand_idx])
        date = "2022-05-" + str(random.randint(1, 31))
        number_of_guests = random.randint(2, 10)
        meeting_hours = (random.randint(0, 18), random.randint(18, 23))
        duration = random.randint(1, 4)
        return {
            "place_types": random_places,
            "date": date,
            "number_of_guests": number_of_guests,
            "meeting_hours": meeting_hours,
            "duration": duration,
            "region_agents_name": region_agents_name
        }


class GroupAgent(Agent):
    def __init__(self, ip, _pass):
        Agent.__init__(self, ip, _pass)
        self._group_dict = {}

    def inform_region_agents(self):
        messages = []
        for region_agent in self._group_dict["region_agents_name"]:
            msg = Message(to=region_agent)
            msg.set_metadata("message_type", "group_request")
            message_body = json.dumps(self._group_dict)
            msg.body = message_body
            messages.append(msg)
        return messages

    def send_question_to_places(self, jids: str):
        messages = []
        split_jids = jids[1:].split(",")
        for jid in split_jids:
            msg = Message(to=jid)
            msg.set_metadata("message_type", "group_question")
            message_body = json.dumps(self._group_dict)
            msg.body = message_body
            messages.append(msg)

        return messages

    class CommunicationWithLeaderBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=10)
            if msg:
                if msg.get_metadata("message_type") == "created_group":
                    self.agent._group_dict = json.loads(msg.body)
                    messages = self.agent.inform_region_agents()
                    for msg in messages:
                        await self.send(msg)
                    self.agent._group_dict["leader"] = str(msg.sender)
                    self.kill()
                elif msg.get_metadata("message_type") == "kill_yourself":
                    print(f"Goodbye word, last words from group agent: {str(self.agent.jid)}")
                    await self.agent.stop()


    class GroupBehaviour(CyclicBehaviour):
        def choose_place(self):
            if len(self.places_yes) == 1:
                place_id = 0
            else:
                place_id = random.randint(0, len(self.places_yes) - 1)
            print(self.places_yes[0]["id"])
            jid = self.places_yes[place_id]["id"]
            msg = Message(to=jid)
            msg.set_metadata("message_type", "group_reservation")
            message_body = json.dumps(self.agent._group_dict)
            msg.body = message_body
            return msg

        async def on_start(self):
            self.count_region_no = 0
            self.count_region_yes = 0
            self.count_places_no = 0
            self.places_yes = []
            self.count_places_send_question = 0
            self.places_jids = ""

        async def run(self):
            msg = await self.receive(timeout=10)
            if msg:
                print("Group received with content: {}".format(msg.body))

                if msg.get_metadata("message_type") == "region_no_agents":
                    self.count_region_no += 1
                    if self.count_region_no == len(self.agent._group_dict["region_agents_name"]):
                        print("I'm gonna kill myself no place to go")
                        await self.agent.stop()
                    elif self.count_region_no + self.count_region_yes == len(
                            self.agent._group_dict["region_agents_name"]):
                        messages = self.agent.send_question_to_places(self.places_jids)
                        for msg in messages:
                            await self.send(msg)

                elif msg.get_metadata("message_type") == "region_yes_reply":
                    self.count_region_yes += 1
                    self.places_jids = self.places_jids + "," + msg.body

                    if self.count_region_no + self.count_region_yes == len(
                            self.agent._group_dict["region_agents_name"]):
                        messages = self.agent.send_question_to_places(self.places_jids)
                        self.count_places_send_question = len(messages)
                        for msg in messages:
                            await self.send(msg)

                elif msg.get_metadata("message_type") == "place_no":
                    self.count_places_no += 1
                    if self.count_places_no == self.count_places_send_question:
                        print("I'm gonna kill myself no place to go")
                        await self.agent.stop()
                    elif self.count_places_no + len(self.places_yes) == self.count_places_send_question:
                        request = self.choose_place()
                        await self.send(request)

                elif msg.get_metadata("message_type") == "place_yes":
                    self.places_yes.append(json.loads(msg.body))
                    if self.count_places_no + len(self.places_yes) == self.count_places_send_question:
                        request = self.choose_place()
                        await self.send(request)
                elif msg.get_metadata("message_type") == "reservation_made":
                    msg_to_leader =Message(to=self.agent._group_dict["leader"])
                    msg_to_leader.body = "reservation made"
                    msg_to_leader.set_metadata("message_type", "reservation_made")
                    await self.send(msg_to_leader)
                    print("I can happily die, I have place to go")
                    await self.agent.stop()

        async def on_end(self):
            print(f"Goodbye word, last words from group agent: {str(self.agent.jid)}")
            await self.agent.stop()

    async def setup(self):
        print(f"Group starting {str(self.jid)}")
        cwlb = self.CommunicationWithLeaderBehaviour()
        self.add_behaviour(cwlb)
        gb = self.GroupBehaviour()
        self.add_behaviour(gb)
