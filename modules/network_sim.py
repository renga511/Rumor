"""
Network Simulation Module
Generates network topology and simulates epidemic spread
"""
import networkx as nx
import numpy as np
import random

# State constants
SUSCEPTIBLE = 0
INFECTED = 1
RECOVERED = 2
IMMUNIZED = 3

def generate_network_data(net_type="Scale-Free (BA)", n=300):
    """Generate network and return JSON-serializable data."""
    n = min(n, 400)  # Cap for browser performance
    
    if net_type == "Scale-Free (BA)":
        G = nx.barabasi_albert_graph(n, 3)
    elif net_type == "Small-World (WS)":
        G = nx.watts_strogatz_graph(n, k=6, p=0.1)
    else:
        G = nx.erdos_renyi_graph(n, p=0.015)

    pos = nx.spring_layout(G, k=0.3, iterations=30, seed=42)

    # Initial states: 3 infected seeds
    states = [SUSCEPTIBLE] * n
    seeds = random.sample(range(n), min(3, n))
    for s in seeds:
        states[s] = INFECTED

    nodes = []
    for i in range(n):
        x, y = pos[i]
        nodes.append({"id": i, "x": float(x), "y": float(y), "state": states[i], "degree": G.degree(i)})

    edges = [{"source": int(u), "target": int(v)} for u, v in G.edges()]
    
    # Build adjacency for simulation
    adjacency = {i: list(G.neighbors(i)) for i in range(n)}

    return {
        "nodes": nodes,
        "edges": edges,
        "adjacency": adjacency,
        "n": n
    }

def simulate_step_data(states, edges, beta, gamma, beta_truth, step, strategy, intervene_step, is_true_news=False):
    """Simulate one timestep and return updated states + metrics."""
    n = len(states)
    
    # Build adjacency from edges
    adj = {i: [] for i in range(n)}
    for e in edges:
        s, t = e["source"], e["target"]
        adj[s].append(t)
        adj[t].append(s)

    new_states = list(states)

    # Apply strategy at intervention step
    if step == intervene_step and strategy != "None":
        new_states = apply_strategy(new_states, adj, strategy, is_true_news)

    # Simulate spread
    infected_nodes = [i for i, s in enumerate(states) if s == INFECTED]
    immunized_nodes = [i for i, s in enumerate(states) if s == IMMUNIZED]

    # Recovery
    for node in infected_nodes:
        if random.random() < gamma:
            new_states[node] = RECOVERED

    # Rumor/fake spread from infected
    for node in infected_nodes:
        if new_states[node] == RECOVERED:
            continue
        for nb in adj.get(node, []):
            if states[nb] == SUSCEPTIBLE:
                # True news believed more readily (higher beta)
                effective_beta = beta * (1.3 if is_true_news else 1.0)
                if random.random() < min(effective_beta, 0.95):
                    new_states[nb] = INFECTED

    # Truth/counter-spread from immunized
    if beta_truth > 0 and not is_true_news:
        for node in immunized_nodes:
            for nb in adj.get(node, []):
                if states[nb] in [SUSCEPTIBLE, INFECTED]:
                    if random.random() < beta_truth:
                        new_states[nb] = IMMUNIZED

    counts = {
        "susceptible": new_states.count(SUSCEPTIBLE),
        "infected": new_states.count(INFECTED),
        "recovered": new_states.count(RECOVERED),
        "immunized": new_states.count(IMMUNIZED),
        "step": step + 1
    }

    return {"states": new_states, "counts": counts, "strategy_applied": step == intervene_step}

def apply_strategy(states, adj, strategy, is_true_news, param=0.05):
    """Apply counter-strategy interventions."""
    n = len(states)
    
    if strategy == "Mass Immunization":
        susceptible = [i for i, s in enumerate(states) if s == SUSCEPTIBLE]
        num = int(n * param)
        chosen = random.sample(susceptible, min(num, len(susceptible)))
        for c in chosen:
            states[c] = IMMUNIZED

    elif strategy == "Influencer Correction (Degree)":
        degrees = [(i, len(nb)) for i, nb in adj.items()]
        degrees.sort(key=lambda x: x[1], reverse=True)
        count, target = 0, int(n * param)
        for node, _ in degrees:
            if states[node] == SUSCEPTIBLE:
                states[node] = IMMUNIZED
                count += 1
            if count >= target:
                break

    elif strategy == "Inject Truth Campaign (Multi-Agent)":
        degrees = [(i, len(nb)) for i, nb in adj.items()]
        degrees.sort(key=lambda x: x[1], reverse=True)
        target = max(2, int(n * 0.03))
        count = 0
        for node, _ in degrees:
            if states[node] != IMMUNIZED:
                states[node] = IMMUNIZED
                count += 1
            if count >= target:
                break

    elif strategy == "Edge Removal (Quarantine)":
        # Mark heavily infected nodes as recovered (quarantined)
        infected = [i for i, s in enumerate(states) if s == INFECTED]
        for node in infected[:max(1, len(infected)//3)]:
            states[node] = RECOVERED

    return states
