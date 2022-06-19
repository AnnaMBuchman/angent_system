from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from place_types import *
import json


class RegionAgent(Agent):
    def __init__(self, ip, _pass, name: str):
        Agent.__init__(self, ip, _pass)
        self._places_dict = {}
        self._name = name
        for type in PlaceTypes:
            self._places_dict[type.name] = []

    def search_for_places(self, group_dict):
        jids = []
        for type in group_dict["place_types"]:
            for place_dict in self._places_dict[type]:
                if place_dict["number_of_guests"] > group_dict["number_of_guests"]:
                    for i in range(group_dict["meeting_hours"][0],
                                   group_dict["meeting_hours"][1] - group_dict["duration"]):
                        if i >= place_dict["open_hours"][0] & i + group_dict["duration"] <= place_dict["open_hours"][1]:
                            jids.append(place_dict["id"])
                            break
        return jids

    def add_place(self, body: str):
        place_dict = json.loads(body)
        self._places_dict[place_dict["place_type"]].append(place_dict)

    class RegionPlaceBehaviour(CyclicBehaviour):
        async def on_start(self):
            print(f"Hell yeah, I am alive, region {self.agent._name} agent")

        async def run(self):
            msg = await self.receive(timeout=3)
            if msg:
                if msg.get_metadata("message_type") == "hello":
                    print(f"{self.agent._name}'s adding place: {msg.body}")
                    self.agent.add_place(msg.body)

                if msg.get_metadata("message_type") == "goodbye":
                    print("Region received with content: {}".format(msg.body))
                    for type in self.agent._places_dict:
                        place_index = next(
                            (index for (index, d) in enumerate(self.agent._places_dict[type]) if d["id"] == msg.body),
                            None)
                        if place_index is not None:
                            del self.agent._places_dict[type][place_index]

    class RegionGroupBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=3)
            if msg:
                if msg.get_metadata("message_type") == "group_request":
                    print("Region received with content: {}".format(msg.body))
                    group_dict = json.loads(msg.body)
                    jids = self.agent.search_for_places(group_dict)
                    sender = str(msg.sender)
                    msg = Message(to=sender)
                    msg.set_metadata("message_type", "region_reply")
                    if len(jids) == 0:
                        msg.set_metadata("message_type", "region_no_agents")
                        msg.body = "I'm sad, I have no place for you"
                    else:
                        msg.set_metadata("message_type", "region_yes_reply")
                        msg.body = ','.join([item for item in jids])
                    await self.send(msg)

        async def on_end(self):
            print(f"Goodbye word, last words from {self.agent.jid}")
            await self.agent.stop()

    async def setup(self):
        print(f"Region starting name: {self._name},jid: {self.jid}")
        rpb = self.RegionPlaceBehaviour()
        self.add_behaviour(rpb)
        rgb = self.RegionGroupBehaviour()
        self.add_behaviour(rgb)
