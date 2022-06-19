from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour
from spade.message import Message
import datetime


class ClockAgent(Agent):
    def __init__(self, ip, _pass, places):
        Agent.__init__(self, ip, _pass)
        self._places = places
        self._day = 2

    def clock_tick(self):
        messages = []
        for place in self._places:
            msg = Message(to=place)
            msg.set_metadata("message_type", "clock_tick")
            msg.body = '2022-05-' + str(self._day)
            messages.append(msg)
        self._day += 1
        return messages

    class ClockBehaviour(PeriodicBehaviour):
        async def run(self):
            for msg in self.agent.clock_tick():
                await self.send(msg)

    async def setup(self):
        print(f"Clock is starting {str(self.jid)}")
        start_at = datetime.datetime.now() + datetime.timedelta(seconds=2)
        cb = self.ClockBehaviour(period=4, start_at=start_at)
        self.add_behaviour(cb)
