import traci
import random
import sys
import os
import time

# Multi-Agent System for Smart Traffic Management
# Context:
# This script simulates a multi-agent system to address urban traffic congestion by dynamically managing traffic signals,
# monitoring traffic conditions using drones, and prioritizing emergency vehicles. The system integrates AI-powered 
# traffic lights, smart vehicles, and drones to reduce congestion and improve emergency response times.

# Key Features:
# - Dynamic traffic signal adjustments based on real-time traffic data.
# - Drone surveillance for incident detection (e.g., accidents, congestion, roadblocks).
# - Emergency vehicle prioritization at intersections.
# - Simulation of various urban traffic scenarios using SUMO (Simulation of Urban Mobility).

# Connect to SUMO
print("Starting SUMO simulation with multi-agent traffic management...")
try:
    # Start the SUMO simulation with the specified configuration file
    traci.start(["sumo-gui", "-c", "simulation.sumocfg"])
    print("Connected to SUMO successfully")
except Exception as e:
    # Handle connection errors
    print(f"Error connecting to SUMO: {e}")
    sys.exit(1)

try:
    # Initialize drone surveillance
    # Drones are used to monitor traffic conditions and detect incidents in real-time
    drone_positions = []
    for i in range(3):  # Create 3 drones for surveillance
        drone_positions.append({
            'id': f'drone_{i}',  # Unique ID for each drone
            'x': random.randint(0, 1000),  # Random initial x-coordinate
            'y': random.randint(0, 1000),  # Random initial y-coordinate
            'detected_incidents': []  # List to store detected incidents
        })
    print(f"Initialized {len(drone_positions)} surveillance drones")
    
    # Visualize drones as Points of Interest (POIs) in SUMO
    for drone in drone_positions:
        traci.poi.add(
            drone['id'],                  # POI ID
            drone['x'], drone['y'],       # Position
            (0, 0, 255, 255),             # Color (RGBA) - blue
            "drone",                      # Type
            3600,                         # Layer
            ""                            # Image URL (not used by SUMO)
        )
    
    # Initialize statistics tracking variables
    total_wait_time = 0  # Total waiting time for all vehicles
    total_vehicles = 0   # Total number of vehicles processed
    emergency_vehicles_detected = 0  # Count of emergency vehicles detected
    incidents_detected = 0  # Count of incidents detected by drones
    
    # Main simulation loop
    step = 0
    print("Beginning simulation loop...")
    while step < 3600:  # Run for 1 hour simulation time
        traci.simulationStep()  # Advance the simulation by one step
        
        # Get traffic light IDs
        tls = traci.trafficlight.getIDList()
        
        for tl in tls:
            # Get the number of vehicles approaching the intersection
            lanes = traci.trafficlight.getControlledLanes(tl)
            vehicles = sum(traci.lane.getLastStepVehicleNumber(lane) for lane in lanes)
            
            # Adaptive traffic signal logic based on vehicle count
            if vehicles > 5:
                # Heavy traffic - extend green phase duration
                traci.trafficlight.setPhaseDuration(tl, 30)
                if step % 100 == 0:  # Log periodically
                    print(f"Traffic light {tl}: Heavy traffic ({vehicles} vehicles) - extending green phase to 30s")
            else:
                # Light traffic - reduce green phase duration
                traci.trafficlight.setPhaseDuration(tl, 15)
                if step % 100 == 0:  # Log periodically
                    print(f"Traffic light {tl}: Light traffic ({vehicles} vehicles) - reducing green phase to 15s")
            
            # Check for emergency vehicles and prioritize them
            emergency_detected = False
            for lane in lanes:
                vehicles_on_lane = traci.lane.getLastStepVehicleIDs(lane)
                for v in vehicles_on_lane:
                    try:
                        if traci.vehicle.getTypeID(v) == "emergency":
                            emergency_detected = True
                            emergency_vehicles_detected += 1
                            # Set all lights to red except the direction of the emergency vehicle
                            curr_lane = traci.vehicle.getLaneID(v)
                            if curr_lane in lanes:
                                # Simplified logic to prioritize emergency vehicles
                                phases = traci.trafficlight.getAllProgramLogics(tl)[0].phases
                                if len(phases) > 0:
                                    state_length = len(phases[0].state)
                                    lane_idx = lanes.index(curr_lane) % state_length
                                    new_state = "r" * state_length
                                    new_state = new_state[:lane_idx] + "G" + new_state[lane_idx+1:]
                                    traci.trafficlight.setRedYellowGreenState(tl, new_state)
                                    print(f"Emergency vehicle detected! Prioritizing traffic light {tl} for vehicle {v}")
                    except traci.exceptions.TraCIException as e:
                        print(f"Error checking vehicle {v}: {e}")
        
        # Update drone positions periodically
        if step % 30 == 0:  # Every 30 steps
            for drone in drone_positions:
                # Move drone randomly within a certain range
                move_x = random.uniform(-50, 50)
                move_y = random.uniform(-50, 50)
                drone['x'] += move_x
                drone['y'] += move_y
                
                # Update drone POI position in SUMO
                try:
                    traci.poi.setPosition(drone['id'], drone['x'], drone['y'])
                except:
                    pass  # Ignore if drone is outside network bounds
        
        # Drone surveillance for incident detection
        if step % 300 == 0:  # Every 5 minutes simulation time
            drone = random.choice(drone_positions)
            
            # Generate a random incident location
            try:
                edges = traci.edge.getIDList()
                if edges:
                    random_edge = random.choice(edges)
                    edge_length = traci.edge.getLength(random_edge)
                    position = random.uniform(0, edge_length)
                    x, y = traci.simulation.convert2D(random_edge, position)
                else:
                    x, y = random.randint(0, 1000), random.randint(0, 1000)
            except:
                x, y = random.randint(0, 1000), random.randint(0, 1000)
            
            # Generate a random incident
            incident_types = ["congestion", "accident", "roadblock", "construction"]
            incident = {
                'type': random.choice(incident_types),
                'location': (x, y),
                'severity': random.uniform(0.1, 1.0),
                'time_detected': step
            }
            
            drone['detected_incidents'].append(incident)
            incidents_detected += 1
            print(f"\nALERT: Drone {drone['id']} detected {incident['type']} at location {incident['location']}")
            print(f"Incident severity: {incident['severity']:.2f} (0-1 scale)")
            
            # Simulate response based on incident type and severity
            if incident['type'] == "accident" and incident['severity'] > 0.7:
                print(f"High severity accident detected! Dispatching emergency vehicle.")
            elif incident['type'] == "congestion" and incident['severity'] > 0.5:
                print(f"Significant congestion detected! Adjusting traffic light timings in the area.")
        
        # Collect and log metrics periodically
        if step % 100 == 0:  # Every 100 steps
            vehicles = traci.vehicle.getIDList()
            total_vehicles = len(vehicles)
            if total_vehicles > 0:
                total_wait_time = sum(traci.vehicle.getWaitingTime(v) for v in vehicles)
                avg_wait_time = total_wait_time / max(1, total_vehicles)
                print(f"Step {step}: Average wait time: {avg_wait_time:.2f}s, Vehicles: {total_vehicles}")
        
        step += 1

    # Print final statistics after simulation ends
    print("\n===== Simulation Complete =====")
    print(f"Total simulation steps: {step}")
    print(f"Total vehicles processed: {total_vehicles}")
    print(f"Emergency vehicles detected: {emergency_vehicles_detected}")
    print(f"Incidents detected by drones: {incidents_detected}")
    if total_vehicles > 0:
        print(f"Final average waiting time: {total_wait_time / max(1, total_vehicles):.2f} seconds")

except Exception as e:
    # Handle errors during simulation
    print(f"Error during simulation: {e}")
finally:
    # Close the TraCI connection
    try:
        if traci.isConnected():
            traci.close()
            print("TraCI connection closed successfully")
    except:
        print("Error closing TraCI connection")