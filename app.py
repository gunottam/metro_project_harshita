import pandas as pd
import heapq
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
import folium
import os
from collections import defaultdict

# Enhanced color definitions with more distinct colors
LINE_COLORS = {
    'Aqua': '#00FFFF',             # Cyan
    'Blue': '#0000FF',             # Blue
    'Blue Branch': '#0000FF',      # Same as Blue
    'Gray': '#808080',             # Gray
    'Green': '#00AA00',            # Darker Green
    'Green Branch': '#00AA00',     # Same as Green
    'Magenta': '#FF00FF',          # Magenta
    'Orange': '#FF8C00',           # Dark Orange
    'Pink': '#FF69B4',             # Hot Pink
    'Rapid Metro': '#800080',      # Purple (distinctive)
    'Red': '#FF0000',              # Red
    'Violet': '#9400D3',           # Dark Violet
    'Yellow': '#FFD700',           # Gold Yellow
}
def normalize_line_name(line):
    line = line.strip().lower()
    if 'blue' in line:
        return 'Blue' if 'branch' not in line else 'Blue Branch'
    elif 'green' in line:
        return 'Green' if 'branch' not in line else 'Green Branch'
    elif 'aqua' in line:
        return 'Aqua'
    elif 'gray' in line or 'grey' in line:
        return 'Gray'
    elif 'magenta' in line:
        return 'Magenta'
    elif 'orange' in line:
        return 'Orange'
    elif 'pink' in line:
        return 'Pink'
    elif 'rapid' in line:
        return 'Rapid Metro'
    elif 'red' in line:
        return 'Red'
    elif 'violet' in line or 'voilet' in line:  # typo catch
        return 'Violet'
    elif 'yellow' in line:
        return 'Yellow'
    else:
        return line.title()


class MetroGraph:
    def __init__(self):
        self.graph = {}
        self.stations = set()
        self.station_coords = {}  # {station: (lat, lon)}
        self.line_edges = defaultdict(set)  # {line: set of (from, to)}
        self.line_stations = defaultdict(set)  # {line: set of stations}
    
    def add_edge(self, from_station, to_station, time, distance, cost, line, lat_from=None, lon_from=None, lat_to=None, lon_to=None):
        line = line.strip().title()  # Normalize line name
        
        if from_station not in self.graph:
            self.graph[from_station] = []
        if to_station not in self.graph:
            self.graph[to_station] = []
        
        self.graph[from_station].append((to_station, time, distance, cost, line))
        self.graph[to_station].append((from_station, time, distance, cost, line))  # Bidirectional
        
        self.stations.add(from_station)
        self.stations.add(to_station)
        self.line_stations[line].update([from_station, to_station])
        
        # Store coordinates
        if lat_from is not None and lon_from is not None:
            self.station_coords[from_station] = (float(lat_from), float(lon_from))
        if lat_to is not None and lon_to is not None:
            self.station_coords[to_station] = (float(lat_to), float(lon_to))
        
        # Store edges by line
        self.line_edges[line].add((from_station, to_station))
    
    def dijkstra(self, start, end, criteria='time'):
        if criteria == 'time':
            weight_index = 1
        elif criteria == 'distance':
            weight_index = 2
        elif criteria == 'cost':
            weight_index = 3
        else:
            raise ValueError("Invalid criteria.")
        
        heap = []
        heapq.heappush(heap, (0, start, [], []))
        visited = set()
        
        while heap:
            total_weight, current, path, lines = heapq.heappop(heap)
            if current in visited:
                continue
            visited.add(current)
            path = path + [current]
            if current == end:
                return {
                    'path': path,
                    'total_time': sum(step[2] for step in self._get_steps(path)),
                    'total_distance': sum(step[3] for step in self._get_steps(path)),
                    'total_cost': sum(step[4] for step in self._get_steps(path)),
                    'lines': lines,
                    'transfers': self._count_transfers(lines)
                }
            for neighbor, time, distance, cost, line in self.graph.get(current, []):
                if neighbor not in visited:
                    new_lines = lines + [line] if not lines else (lines if lines[-1] == line else lines + [line])
                    weight = time if criteria == 'time' else distance if criteria == 'distance' else cost
                    heapq.heappush(heap, (total_weight + weight, neighbor, path, new_lines))
        return None
    
    def _get_steps(self, path):
        steps = []
        for i in range(len(path)-1):
            from_station = path[i]
            to_station = path[i+1]
            for neighbor, time, distance, cost, line in self.graph[from_station]:
                if neighbor == to_station:
                    steps.append((from_station, to_station, time, distance, cost, line))
                    break
        return steps
    
    def _count_transfers(self, lines):
        if not lines:
            return 0
        transfers = 0
        current_line = lines[0]
        for line in lines[1:]:
            if line != current_line:
                transfers += 1
                current_line = line
        return transfers
    
    def generate_route_map(self, route):
        """Generate a folium map showing the route with colored lines."""
        if not route or 'path' not in route or len(route['path']) < 2:
            return None
        
        # Get center of the route
        route_coords = [self.station_coords.get(station) for station in route['path'] if station in self.station_coords]
        if not route_coords:
            return None
            
        avg_lat = sum(coord[0] for coord in route_coords) / len(route_coords)
        avg_lon = sum(coord[1] for coord in route_coords) / len(route_coords)
        
        m = folium.Map(location=[avg_lat, avg_lon], zoom_start=13, tiles='CartoDB positron')
        
        # Plot all stations as small markers
        for station, coord in self.station_coords.items():
            folium.CircleMarker(
                location=coord,
                radius=3,
                popup=station,
                color='black',
                fill=True,
                fill_color='white',
                fill_opacity=1,
                weight=1
            ).add_to(m)
        
        # Plot the route with colored lines
        steps = self._get_steps(route['path'])
        for step in steps:
            from_station, to_station, time, distance, cost, line = step
            coord1 = self.station_coords.get(from_station)
            coord2 = self.station_coords.get(to_station)
            
            if coord1 and coord2:
                # Get line color or generate a random one if not defined
                line_color = LINE_COLORS.get(line, '#000000')
                
                folium.PolyLine(
                    locations=[coord1, coord2],
                    color=line_color,
                    weight=6,
                    opacity=0.9,
                    tooltip=f"{line} Line: {from_station} to {to_station}",
                    line_cap='round',
                    line_join='round'
                ).add_to(m)
                
                # Highlight stations on the route
                for station in [from_station, to_station]:
                    coord = self.station_coords.get(station)
                    if coord:
                        folium.CircleMarker(
                            location=coord,
                            radius=5,
                            popup=f"{station} ({line} Line)",
                            color=line_color,
                            fill=True,
                            fill_color=line_color,
                            fill_opacity=1,
                            weight=2
                        ).add_to(m)
        
        return m
    
    def generate_full_map(self):
        """Generate a full metro map with all stations and colored lines."""
        if not self.station_coords:
            return None
            
        # Calculate map center
        latitudes = [coord[0] for coord in self.station_coords.values()]
        longitudes = [coord[1] for coord in self.station_coords.values()]
        center_lat = sum(latitudes)/len(latitudes)
        center_lon = sum(longitudes)/len(longitudes)
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=12, tiles='CartoDB positron')
        
        # Plot all stations
        for station, coord in self.station_coords.items():
            folium.CircleMarker(
                location=coord,
                radius=3,
                popup=station,
                color='black',
                fill=True,
                fill_color='white',
                fill_opacity=1,
                weight=1
            ).add_to(m)
        
        # Draw all lines with their respective colors
        for line, edges in self.line_edges.items():
            line_color = LINE_COLORS.get(line, '#000000')
            
            for edge in edges:
                st1, st2 = edge
                coord1 = self.station_coords.get(st1)
                coord2 = self.station_coords.get(st2)
                
                if coord1 and coord2:
                    folium.PolyLine(
                        locations=[coord1, coord2],
                        color=line_color,
                        weight=4,
                        opacity=0.8,
                        tooltip=f"{line} Line",
                        line_cap='round',
                        line_join='round'
                    ).add_to(m)
        
        # Add legend
        self._add_legend(m)
        
        return m
    
    def _add_legend(self, m):
        """Add a legend to the map showing line colors."""
        legend_html = '''
            <div style="position: fixed; 
                        bottom: 50px; left: 50px; width: 180px; height: auto;
                        border:2px solid grey; z-index:9999; font-size:14px;
                        background-color:white;
                        padding: 10px;">
                <b>Metro Lines</b><br>
        '''
        
        # Add each line with its color
        for line, color in LINE_COLORS.items():
            if line in self.line_stations:  # Only show lines that exist in the data
                legend_html += f'''
                    <div style="margin: 5px 0;">
                        <i class="fa fa-square" style="color:{color};font-size:20px;"></i> {line}
                    </div>
                '''
        
        legend_html += '</div>'
        
        m.get_root().html.add_child(folium.Element(legend_html))


class MetroRouteOptimizerApp:
    def __init__(self, root, metro_graph):
        self.root = root
        self.metro_graph = metro_graph
        self.root.title("Metro Route Optimizer")
        
        # Make window larger
        self.root.geometry("800x700")
        
        self.setup_ui()
    
    def setup_ui(self):
        # Create main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Input frame
        input_frame = ttk.LabelFrame(main_frame, text="Route Options", padding="10")
        input_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(input_frame, text="From Station:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.from_station = ttk.Combobox(input_frame, values=sorted(self.metro_graph.stations))
        self.from_station.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        
        ttk.Label(input_frame, text="To Station:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.to_station = ttk.Combobox(input_frame, values=sorted(self.metro_graph.stations))
        self.to_station.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)
        
        ttk.Label(input_frame, text="Optimize By:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.criteria = ttk.Combobox(input_frame, values=["Shortest Path (Distance)", "Minimum Time", "Minimum Cost"])
        self.criteria.current(0)
        self.criteria.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=5)
        
        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        find_route_btn = ttk.Button(button_frame, text="Find Optimal Route", command=self.find_route)
        find_route_btn.pack(side=tk.LEFT, padx=5)
        
        self.show_route_map_btn = ttk.Button(button_frame, text="Show Route on Map", command=self.show_route_map, state=tk.DISABLED)
        self.show_route_map_btn.pack(side=tk.LEFT, padx=5)
        
        self.show_full_map_btn = ttk.Button(button_frame, text="Show Full Metro Map", command=self.show_full_map)
        self.show_full_map_btn.pack(side=tk.LEFT, padx=5)
        
        # Results frame
        results_frame = ttk.LabelFrame(main_frame, text="Route Details", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.results_text = tk.Text(results_frame, height=15, wrap=tk.WORD)
        self.results_text.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_text['yscrollcommand'] = scrollbar.set
        
        self.current_route = None
    
    def find_route(self):
        from_station = self.from_station.get()
        to_station = self.to_station.get()
        criteria = self.criteria.get()
        
        if not from_station or not to_station:
            messagebox.showerror("Error", "Please select both from and to stations.")
            return
        
        if from_station == to_station:
            messagebox.showerror("Error", "From and To stations cannot be the same.")
            return
        
        criteria_map = {
            "Shortest Path (Distance)": "distance",
            "Minimum Time": "time",
            "Minimum Cost": "cost"
        }
        
        try:
            result = self.metro_graph.dijkstra(from_station, to_station, criteria_map[criteria])
            
            if not result:
                self.results_text.delete(1.0, tk.END)
                self.results_text.insert(tk.END, f"No route found from {from_station} to {to_station}.")
                self.show_route_map_btn.config(state=tk.DISABLED)
                return
            
            self.current_route = result
            self.results_text.delete(1.0, tk.END)
            
            self.results_text.insert(tk.END, f"Optimal Route ({criteria}):\n")
            self.results_text.insert(tk.END, " → ".join(result['path']) + "\n\n")
            
            self.results_text.insert(tk.END, f"Total Stops: {len(result['path']) - 1}\n")
            self.results_text.insert(tk.END, f"Total Time: {result['total_time']} minutes\n")
            self.results_text.insert(tk.END, f"Total Distance: {result['total_distance']} km\n")
            self.results_text.insert(tk.END, f"Total Cost: ₹{result['total_cost']}\n")
            self.results_text.insert(tk.END, f"Line Transfers: {result['transfers']}\n\n")
            
            self.results_text.insert(tk.END, "Step-by-step Directions:\n")
            steps = self.metro_graph._get_steps(result['path'])
            current_line = steps[0][5] if steps else None
            
            for i, step in enumerate(steps, 1):
                from_s, to_s, time, distance, cost, line = step
                if line != current_line:
                    self.results_text.insert(tk.END, f"  - Transfer from {current_line} line to {line} line\n")
                    current_line = line
                self.results_text.insert(tk.END, f"{i}. Take {line} line from {from_s} to {to_s} ({time} min, {distance} km, ₹{cost})\n")
            
            self.show_route_map_btn.config(state=tk.NORMAL)
            
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
            self.show_route_map_btn.config(state=tk.DISABLED)
            self.current_route = None
    
    def show_route_map(self):
        if not self.current_route:
            messagebox.showinfo("Info", "No route to show on map. Please find a route first.")
            return
        
        m = self.metro_graph.generate_route_map(self.current_route)
        if m:
            file_path = "route_map.html"
            m.save(file_path)
            webbrowser.open('file://' + os.path.realpath(file_path))
        else:
            messagebox.showerror("Error", "Could not generate map for the route.")
    
    def show_full_map(self):
        m = self.metro_graph.generate_full_map()
        if m:
            file_path = "full_metro_map.html"
            m.save(file_path)
            webbrowser.open('file://' + os.path.realpath(file_path))
        else:
            messagebox.showerror("Error", "Could not generate full metro map.")


def load_metro_data(file_path, price_per_km=5):  # Set your desired price per km here
    metro_graph = MetroGraph()
    try:
        df = pd.read_csv(file_path)
        print(f"Loaded {len(df)} records from {file_path}")
        
        unique_lines = df['Line'].unique()
        print("Lines in CSV:", unique_lines)
        
        for _, row in df.iterrows():
            # Calculate cost based on distance and price_per_km
            distance = row['Distance (km)']
            cost = distance * price_per_km
            metro_graph.add_edge(
                row['From Station'],
                row['To Station'],
                row['Time (min)'],
                distance,
                cost,
                row['Line'],
                lat_from=row.get('From Lat'),
                lon_from=row.get('From Lon'),
                lat_to=row.get('To Lat'),
                lon_to=row.get('To Lon')
            )
        
        print(f"Graph contains {len(metro_graph.stations)} stations and {len(metro_graph.line_edges)} lines")
        print("Lines in graph:", metro_graph.line_edges.keys())
        
    except Exception as e:
        print(f"Error loading metro data: {e}")
        raise
    return metro_graph


def main():
    try:
        metro_graph = load_metro_data('metro_normalized.csv')
        
        root = tk.Tk()
        app = MetroRouteOptimizerApp(root, metro_graph)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Startup Error", f"Failed to initialize application: {str(e)}")


if __name__ == "__main__":
    main()