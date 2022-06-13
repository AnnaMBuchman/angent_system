from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import random
import json
from place_types import *
from regions_names import RegionNames


class NormalUserAgent(Agent):
    def __init__(self, ip, _pass,):
        Agent.__init__(self, ip, _pass)

    def invitation_answer_leader(self, msg_receive):
        sender = str(msg_receive.sender)
        msg = Message(to=sender)
        if random.choice([True, False]):
            body = json.loads(msg_receive.body)
            region = random.choice(list(body["regions"].keys()))
            start_time = random.randint(body["leader_meeting_hours"][0],
                                        body["leader_meeting_hours"][1] - body["leader_duration"])
            end_time = random.randint(start_time + body["leader_duration"],
                                      body["leader_meeting_hours"][1])
            place_type = random.choice([e.name for e in PlaceTypes])
            msg.set_metadata("message_type", "user_invitation_answer")
            answer_dict = {
                "region": region,
                "free_hours": (start_time, end_time),
                "place_type": place_type
            }
            message_body = json.dumps(answer_dict)
            msg.body = message_body
        else:
            msg.set_metadata("message_type", "no_user")
            msg.body = "I'm in bad mood"
        return msg

    class CommunicationWithLeaderBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=10)
            if msg:
                print("User received with content: {}".format(msg.body))
                if msg.get_metadata("message_type") == "leader_invitation":
                    answer = self.agent.invitation_answer_leader(msg)
                    await self.send(answer)

        async def on_end(self):
            print(f"Goodbye word, last words from user agent: {str(self.agent.jid)}")
            await self.agent.stop()

    async def setup(self):
        print(f"User starting {str(self.jid)}")
        cwlb = self.CommunicationWithLeaderBehaviour()
        self.add_behaviour(cwlb)
