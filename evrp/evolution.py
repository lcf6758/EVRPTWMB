from .model import *
from .util import *
from .operation import *


class VNS_TS_Evolution:
    # 构造属性
    model = None

    vns_neighbour_Rts = 4
    vns_neighbour_max = 5
    eta_feas = 50
    eta_dist = 20
    Delta_SA = 0.08

    penalty_0 = (10, 10, 10)
    penalty_min = tuple()
    penalty_max = tuple()
    delta = 0.0
    eta_penalty = 0

    nu_min = 0
    nu_max = 0
    lambda_div = 0.0
    eta_tabu = 0
    # 计算属性
    vns_neighbour = []

    def __init__(self, model: Model, **param) -> None:
        self.model = model
        for key, value in param.items():
            assert(hasattr(self, key))
            setattr(self, key, value)

    def random_create(self) -> Solution:
        x = random.uniform(self.model.get_map_bound()[0], self.model.get_map_bound()[1])
        y = random.uniform(self.model.get_map_bound()[2], self.model.get_map_bound()[3])
        choose = self.model.customers[:]
        choose.sort(key=lambda cus: Util.cal_angle_AoB((self.model.depot.x, self.model.depot.y), (x, y), (cus.x, cus.y)))
        routes = []
        building_route_visit = [self.model.depot, self.model.depot]

        choose_index = 0
        while choose_index < len(choose):
            allow_insert_place = list(range(1, len(building_route_visit)))

            while True:
                min_increase_dis = float('inf')
                decide_insert_place = None
                for insert_place in allow_insert_place:
                    increase_dis = choose[choose_index].distance_to(building_route_visit[insert_place-1])+choose[choose_index].distance_to(building_route_visit[insert_place])-building_route_visit[insert_place-1].distance_to(building_route_visit[insert_place])
                    if increase_dis < min_increase_dis:
                        decide_insert_place = insert_place
                if len(allow_insert_place) == 1:
                    break
                elif (isinstance(building_route_visit[decide_insert_place-1], Customer) and isinstance(building_route_visit[decide_insert_place], Customer)) and (building_route_visit[decide_insert_place-1].ready_time <= choose[choose_index].ready_time and choose[choose_index].ready_time <= building_route_visit[decide_insert_place].ready_time):
                    break
                elif (isinstance(building_route_visit[decide_insert_place-1], Customer) and not isinstance(building_route_visit[decide_insert_place], Customer)) and building_route_visit[decide_insert_place-1].ready_time <= choose[choose_index].ready_time:
                    break
                elif (not isinstance(building_route_visit[decide_insert_place-1], Customer) and isinstance(building_route_visit[decide_insert_place], Customer)) and choose[choose_index].ready_time <= building_route_visit[decide_insert_place]:
                    break
                elif not isinstance(building_route_visit[decide_insert_place-1], Customer) and not isinstance(building_route_visit[decide_insert_place], Customer):
                    break
                else:
                    allow_insert_place.remove(decide_insert_place)
                    continue

            building_route_visit.insert(decide_insert_place, choose[choose_index])

            try_route = Route(building_route_visit)
            if try_route.feasible_weight(self.model.vehicle) and try_route.feasible_battery(self.model.vehicle):
                del choose[choose_index]
            else:
                if len(routes) < self.model.max_vehicle-1:
                    del building_route_visit[decide_insert_place]
                    if len(building_route_visit) == 2:
                        choose_index += 1
                    else:
                        routes.append(Route(building_route_visit))
                        building_route_visit = [self.model.depot, self.model.depot]
                elif len(routes) == self.model.max_vehicle-1:
                    del choose[choose_index]

        routes.append(Route(building_route_visit[:-1]+choose+[self.model.depot]))

        return Solution(routes)

    def create_vns_neighbour(self, Rts: int, max: int) -> list:
        assert Rts >= 2 and max >= 1
        self.vns_neighbour = []
        for R in range(2, Rts+1):
            for m in range(1, max+1):
                self.vns_neighbour.append((R, m))

    def tabu_search(self, S: Solution, eta_tabu: int) -> Solution:
        return S

    def main(self) -> Solution:
        self.create_vns_neighbour(self.vns_neighbour_Rts, self.vns_neighbour_max)
        S = self.random_create_vnsts()
        k = 0
        i = 0
        feasibilityPhase = True
        acceptSA = Util.SA(self.Delta_SA, self.eta_dist)
        while feasibilityPhase or i < self.eta_dist:
            S1 = Operation.cyclic_exchange(S, *self.vns_neighbour[k])
            S2 = self.tabu_search(S1, self.eta_tabu)
            if random.random() < acceptSA.probability(S2.get_objective(self.model, self.penalty_0), S.get_objective(self.model, self.penalty_0), i):
                S = S2
                print(i, S)
                print(S.feasible(self.model), S.sum_distance())
                k = 0
            else:
                k = (k+1) % len(self.vns_neighbour)
            if feasibilityPhase:
                if not S.feasible(self.model):
                    if i == self.eta_feas:
                        S.addVehicle(self.model)
                        i -= 1
                else:
                    feasibilityPhase = False
                    i -= 1
            i += 1
        return S


class DEMA_Evolution:
    # 构造属性
    model = None
    penalty = (15, 5, 10)
    maxiter_evo = 10
    size = 30
    cross_prob = 0.7
    infeasible_proportion = 0.25
    sigma = (1, 5, 10)
    theta = 0.5
    maxiter_tabu_multiply = 4
    max_neighbour_multiply = 3
    tabu_len = 4
    # 状态属性
    cross_score = [0.0, 0.0]
    cross_call_times = [0, 0]
    cross_weigh = [0.0, 0.0]

    def __init__(self, model: Model, **param) -> None:
        self.model = model
        for key, value in param.items():
            assert(hasattr(self, key))
            setattr(self, key, value)

    def random_create(self) -> Solution:
        x = random.uniform(self.model.get_map_bound()[0], self.model.get_map_bound()[1])
        y = random.uniform(self.model.get_map_bound()[2], self.model.get_map_bound()[3])
        choose = self.model.customers[:]
        choose.sort(key=lambda cus: Util.cal_angle_AoB((self.model.depot.x, self.model.depot.y), (x, y), (cus.x, cus.y)))
        routes = []
        building_route_visit = [self.model.depot, self.model.depot]

        choose_index = 0
        while choose_index < len(choose):
            allow_insert_place = list(range(1, len(building_route_visit)))

            while True:
                min_increase_dis = float('inf')
                decide_insert_place = None
                for insert_place in allow_insert_place:
                    increase_dis = choose[choose_index].distance_to(building_route_visit[insert_place-1])+choose[choose_index].distance_to(building_route_visit[insert_place])-building_route_visit[insert_place-1].distance_to(building_route_visit[insert_place])
                    if increase_dis < min_increase_dis:
                        decide_insert_place = insert_place
                if len(allow_insert_place) == 1:
                    break
                elif (isinstance(building_route_visit[decide_insert_place-1], Customer) and isinstance(building_route_visit[decide_insert_place], Customer)) and (building_route_visit[decide_insert_place-1].ready_time <= choose[choose_index].ready_time and choose[choose_index].ready_time <= building_route_visit[decide_insert_place].ready_time):
                    break
                elif (isinstance(building_route_visit[decide_insert_place-1], Customer) and not isinstance(building_route_visit[decide_insert_place], Customer)) and building_route_visit[decide_insert_place-1].ready_time <= choose[choose_index].ready_time:
                    break
                elif (not isinstance(building_route_visit[decide_insert_place-1], Customer) and isinstance(building_route_visit[decide_insert_place], Customer)) and choose[choose_index].ready_time <= building_route_visit[decide_insert_place]:
                    break
                elif not isinstance(building_route_visit[decide_insert_place-1], Customer) and not isinstance(building_route_visit[decide_insert_place], Customer):
                    break
                else:
                    allow_insert_place.remove(decide_insert_place)
                    continue

            building_route_visit.insert(decide_insert_place, choose[choose_index])

            try_route = Route(building_route_visit)
            if try_route.feasible_weight(self.model.vehicle) and try_route.feasible_time(self.model.vehicle):
                #del choose[choose_index]
                choose_index += 1
            else:
                del building_route_visit[decide_insert_place]
                assert len(building_route_visit) != 2
                routes.append(Route(building_route_visit))
                building_route_visit = [self.model.depot, self.model.depot]

        routes.append(Route(building_route_visit))

        return Solution(routes)

    def abondon_random_create(self) -> Solution:
        choose = self.model.customers[:]
        random.shuffle(choose)
        routes = []
        building_route_visit = [self.model.depot]
        i = 0
        while i < len(choose):
            try_route = Route(building_route_visit+[choose[i], self.model.depot])
            if try_route.feasible_weight(self.model.vehicle) and try_route.feasible_time(self.model.vehicle):
                if i == len(choose)-1:
                    routes.append(try_route)
                    break
                building_route_visit.append(choose[i])
                i += 1
            else:
                building_route_visit.append(self.model.depot)
                routes.append(Route(building_route_visit))
                building_route_visit = [self.model.depot]
        return Solution(routes)

    def initialization(self) -> list:
        population = []
        for _ in range(self.size):
            sol = self.random_create()
            sol, _ = Operation.charging_modification(sol, self.model)
            population.append(sol)
        return population

    def ACO_GM(self, P: list) -> list:
        fes_P = []
        infes_P = []
        for sol in P:
            if sol.feasible(self.model):
                fes_P.append(sol)
            else:
                infes_P.append(sol)
        fes_P.sort(key=lambda sol: sol.get_objective(self.model, self.penalty))
        obj_value = []
        for sol in infes_P:
            overlapping_degree = Operation.overlapping_degree_population(sol, P)
            objective = sol.get_objective(self.model, self.penalty)
            obj_value.append([objective, overlapping_degree])
        infes_P = Util.pareto_sort(infes_P, obj_value)
        P = fes_P+infes_P
        choose = Util.binary_tournament(len(P))
        P_parent = []
        for i in choose:
            P_parent.append(P[i])
        P_child = []
        while len(P_child) < self.size:
            for i in range(2):
                if self.cross_call_times[i] == 0:
                    self.cross_weigh[i] = self.cross_weigh[i]
                else:
                    self.cross_weigh[i] = self.theta*np.pi/self.cross_call_times[i]+(1-self.theta)*self.cross_weigh[i]
            if self.cross_weigh[0] == 0 and self.cross_weigh[1] == 0:
                sel_prob = np.array([0.5, 0.5])
            else:
                sel_prob = np.array(self.cross_weigh)/np.sum(np.array(self.cross_weigh))
            sel = Util.wheel_select(sel_prob)

            if sel == 0:
                S_parent = random.choice(P_parent)
                S = Operation.ACO_GM_cross1(S_parent)
            elif sel == 1:
                S_parent, S2 = random.sample(P_parent, 2)
                S = Operation.ACO_GM_cross2(S_parent, S2)

            self.cross_call_times[sel] += 1
            cost = S.get_objective(self.model, self.penalty)
            all_cost = [sol.get_objective(self.model, self.penalty) for sol in P]
            if cost < all(all_cost):
                self.cross_score[sel] += self.sigma[0]
            elif cost < S_parent.get_objective(self.model, self.penalty):
                self.cross_score[sel] += self.sigma[1]
            else:
                self.cross_score[sel] += self.sigma[2]

            P_child.append(S)
        return P_child

    def ISSD(self, P: list) -> list:
        pass

    def MVS(self, P: list) -> list:
        pass

    def update_S(self, P: list, S_best: Solution, cost: float) -> Solution:
        min_cost = cost
        S_best = S_best
        for S in P:
            cost = S.get_objective(self.model, self.penalty)
            if cost < min_cost:
                S_best = S
                min_cost = cost
        return S_best, min_cost

    def main(self) -> Solution:
        P = self.initialization()
        S_best, min_cost = self.update_S(P, None, float('inf'))
        for iter in range(self.maxiter_evo):
            print(iter, min_cost)
            P_child = self.ACO_GM(P)
            P = P_child
            S_best, min_cost = self.update_S(P, S_best, min_cost)
        return S_best, min_cost