from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from place_types import *
import json
import random
import randomname
import datetime


class PlaceAgentUtils:
    @staticmethod
    def create_place_dict(place_name: str, place_type: PlaceTypes, location: (float, float), number_of_guests: int,
                          open_hours: (int, int), region_agent_name: str, price_per_person: int):
        if open_hours[0] < 0 | open_hours[0] > 23 | open_hours[1] < 0 | open_hours[1] > 23:
            raise ValueError("Wrong open hours it should be from 0 to 23")
        if open_hours[0] >= open_hours[1] < 0:
            raise ValueError("Wrong open hours second value should be larger than first")
        return {
            "place_name": place_name,
            "place_type": place_type.name,
            "location": location,
            "number_of_guests": number_of_guests,
            "open_hours": open_hours,
            "region_agent_name": region_agent_name,
            "price_per_person": price_per_person,
            "special_price": {}
        }

    @staticmethod
    def generate_random_place_dict(region_agent_name):
        place_name = randomname.get_name(noun=('gaming', 'music_instruments', 'astronomy'))
        place_type = random.choice(list(PlaceTypes))
        location = (random.uniform(51.0, 53.0), random.uniform(51.0, 53.0))
        number_of_guests = random.randint(5, 20)
        open_hour = random.randint(0, 18)
        close_hour = random.randint(open_hour, 23)
        price_per_person = random.randint(3, 40)
        return {
            "place_name": place_name,
            "place_type": place_type.name,
            "location": location,
            "number_of_guests": number_of_guests,
            "open_hours": (open_hour, close_hour),
            "region_agent_name": region_agent_name,
            "price_per_person": price_per_person,
            "special_price": {}
        }


class PlaceAgent(Agent):
    def __init__(self, ip, _pass, place_dict: dict):
        Agent.__init__(self, ip, _pass)
        self._place_dict = place_dict
        self._place_dict["id"] = f"{self.jid[0]}@{self.jid[1]}/{self.jid[2]}"
        self._reservation_calendar = {}

    def special_price(self, date: str):
        value = random.randint(1, self._place_dict["price_per_person"])
        self._place_dict["special_price"][date] = value

    def inform_region_agent(self):
        msg = Message(to=self._place_dict["region_agent_name"])
        msg.set_metadata("message_type", "hello")
        dict_for_region = {"place_name": self._place_dict["place_name"],
                           "place_type": self._place_dict["place_type"],
                           "number_of_guests": self._place_dict["number_of_guests"],
                           "open_hours": self._place_dict["open_hours"],
                           "id": self._place_dict["id"]}
        message_body = json.dumps(dict_for_region)
        msg.body = message_body
        return msg

    def delete_me_region_agent(self):
        msg = Message(to=self._place_dict["region_agent_name"])
        msg.set_metadata("message_type", "goodbye")
        msg.body = self._place_dict["id"]
        return msg

    def check_if_reservation_possible(self, group_dict):
        return True

    def make_reservation(self, sender, group_dict):
        if group_dict["date"] not in self._reservation_calendar:
            self._reservation_calendar[group_dict["date"]] = group_dict["number_of_guests"]
        else:
            self._reservation_calendar[group_dict["date"]] += group_dict["number_of_guests"]
        msg = Message(to=sender)
        msg.set_metadata("message_type", "reservation_made")
        msg.body = "See you"
        return msg

    class PlaceBehaviour(CyclicBehaviour):
        async def on_start(self):
            msg = self.agent.inform_region_agent()
            await self.send(msg)

        async def run(self):
            msg = await self.receive(timeout=10)
            if msg:
                print("Place received with content: {}".format(msg.body))
                if msg.get_metadata("message_type") == "group_question":
                    body = json.loads(msg.body)
                    sender = str(msg.sender)
                    response = Message(to=sender)
                    if self.agent.check_if_reservation_possible(body):
                        print("Reservation is possible")
                        response.set_metadata("message_type", "place_yes")
                        response.body = json.dumps(self.agent._place_dict)
                    else:
                        print("Reservation is not possible")
                        response.set_metadata("message_type", "place_no")
                        response.body = "no"
                    await self.send(response)
                elif msg.get_metadata("message_type") == "group_reservation":
                    print("I'm making reservation")
                    response = self.agent.make_reservation(str(msg.sender), json.loads(msg.body))
                    await self.send(response)

        async def on_end(self):
            msg = self.agent.delete_me_region_agent()
            await self.send(msg)
            print(f"Goodbye word, last words from {str(self.agent.jid)}")
            await self.agent.stop()

    async def setup(self):
        print(f"Place starting {str(self.jid)}")
        pb = self.PlaceBehaviour()
        self.add_behaviour(pb)
