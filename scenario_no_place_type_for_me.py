import time
from place_agent import *
from region_agent import *
from group_agent import *
from normal_user_agent import *
from regions_names import *
from leader_agent import *
from clock_agent import *

if __name__ == "__main__":
    regions = 1
    places = 5
    users = 15
    leaders = 10
    address = "<XMPP mail>"
    password = "<password>"
    region_agents = {}
    region_agents_ids = {}
    for i in range(regions):
        region_agents[RegionNames(i + 1).name] = RegionAgent(address + str(i), password, RegionNames(i + 1).name)
        region_agents_ids[RegionNames(i + 1).name] = address + str(i)
        future = region_agents[RegionNames(i + 1).name].start()
        future.result()
    place_agents = []
    place_agents_ids = []
    for i in range(regions, regions + places):
        rand_region = random.randint(1, regions)
        place_dict = PlaceAgentUtils.generate_random_place_dict_one_type(
            str(region_agents[RegionNames(rand_region).name].jid))
        place_agents.append(PlaceAgent(address + str(i), password, place_dict))
        place_agents_ids.append(address + str(i))
        future = place_agents[i - regions].start()
        future.result()

    user_agents = []
    user_ids = []
    for i in range(regions + places, regions + places + users):
        user_agents.append(NormalUserAgent(address + str(i), password))
        user_ids.append(address + str(i))
        future = user_agents[i - regions - places].start()
        future.result()
    leader_agents = []
    group_agents = []
    time.sleep(1)
    clock_agent = ClockAgent(address + str(1001), password, place_agents_ids)
    future = clock_agent.start()
    future.result()

    for i in range(regions + places + users, regions + places + users + leaders):
        group_agents.append(GroupAgent(address + str(i), password))
        future = group_agents[i - regions - places - users].start()
        future.result()
        leaders_dict = LeaderAgentUtils.create_random_leader_dict(user_ids, address + str(i),
                                                                                region_agents_ids)
        leader_agents.append(LeaderAgent(address + str(i + leaders), password, leaders_dict))
        leader_agents[i - regions - places - users].start()
        time.sleep(1)

    while region_agents["Mokotow"].is_alive():
        try:
            time.sleep(100)
        except KeyboardInterrupt:
            for agent in region_agents:
                agent.stop()
            for agent in place_agents:
                agent.stop()
            for agent in group_agents:
                agent.stop()
            for agent in leader_agents:
                agent.stop()
            for agent in user_agents:
                agent.stop()
            break

    print("Agents finished")
