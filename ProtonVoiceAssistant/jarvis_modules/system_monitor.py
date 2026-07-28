"""
Jarvis System Monitoring Module
Advanced system monitoring and diagnostics
"""
import psutil
import platform
from datetime import datetime

class SystemMonitor:
    def __init__(self):
        pass
    
    def get_system_status(self):
        """Get comprehensive system status"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network stats
            net_io = psutil.net_io_counters()
            
            # Battery
            battery = psutil.sensors_battery()
            battery_info = ""
            if battery:
                battery_info = f"Battery: {battery.percent}% ({'Charging' if battery.power_plugged else 'Not charging'})"
            else:
                battery_info = "Battery: Not available"
            
            status = f"""System Status:
CPU Usage: {cpu_percent}%
Memory: {memory.percent}% used ({memory.used / (1024**3):.2f} GB / {memory.total / (1024**3):.2f} GB)
Disk: {disk.percent}% used ({disk.used / (1024**3):.2f} GB / {disk.total / (1024**3):.2f} GB)
{battery_info}
Network: Sent {net_io.bytes_sent / (1024**2):.2f} MB, Received {net_io.bytes_recv / (1024**2):.2f} MB
OS: {platform.system()} {platform.release()}
"""
            return status
        except Exception as e:
            return f"Failed to get system status: {str(e)}"
    
    def get_cpu_info(self):
        """Get CPU information"""
        try:
            cpu_count = psutil.cpu_count()
            cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
            cpu_freq = psutil.cpu_freq()
            
            info = f"CPU Cores: {cpu_count}\n"
            info += f"CPU Frequency: {cpu_freq.current:.2f} MHz\n"
            info += f"Overall CPU Usage: {sum(cpu_percent) / len(cpu_percent):.1f}%\n"
            
            return info
        except Exception as e:
            return f"Failed to get CPU info: {str(e)}"
    
    def get_memory_info(self):
        """Get detailed memory information"""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            info = f"""Memory Information:
Total: {memory.total / (1024**3):.2f} GB
Available: {memory.available / (1024**3):.2f} GB
Used: {memory.used / (1024**3):.2f} GB ({memory.percent}%)
Free: {memory.free / (1024**3):.2f} GB
Swap Total: {swap.total / (1024**3):.2f} GB
Swap Used: {swap.used / (1024**3):.2f} GB
"""
            return info
        except Exception as e:
            return f"Failed to get memory info: {str(e)}"
    
    def get_disk_info(self):
        """Get disk usage information"""
        try:
            partitions = psutil.disk_partitions()
            info = "Disk Information:\n"
            
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    info += f"\n{partition.device} ({partition.mountpoint}):\n"
                    info += f"  Total: {usage.total / (1024**3):.2f} GB\n"
                    info += f"  Used: {usage.used / (1024**3):.2f} GB ({usage.percent}%)\n"
                    info += f"  Free: {usage.free / (1024**3):.2f} GB\n"
                except:
                    continue
            
            return info
        except Exception as e:
            return f"Failed to get disk info: {str(e)}"
    
    def get_running_processes(self, top_n=10):
        """Get top N processes by CPU usage"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append(proc.info)
                except:
                    continue
            
            # Sort by CPU usage
            processes.sort(key=lambda x: x['cpu_percent'] or 0, reverse=True)
            
            info = f"Top {top_n} Processes by CPU:\n"
            for i, proc in enumerate(processes[:top_n], 1):
                info += f"{i}. {proc['name']}: CPU {proc['cpu_percent']:.1f}%, Memory {proc['memory_percent']:.1f}%\n"
            
            return info
        except Exception as e:
            return f"Failed to get processes: {str(e)}"
    
    def check_system_health(self):
        """Check overall system health and provide warnings"""
        warnings = []
        
        try:
            # Check CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 80:
                warnings.append(f"High CPU usage: {cpu_percent}%")
            
            # Check Memory
            memory = psutil.virtual_memory()
            if memory.percent > 85:
                warnings.append(f"High memory usage: {memory.percent}%")
            
            # Check Disk
            disk = psutil.disk_usage('/')
            if disk.percent > 90:
                warnings.append(f"Low disk space: {disk.percent}% used")
            
            # Check Battery
            battery = psutil.sensors_battery()
            if battery and not battery.power_plugged and battery.percent < 20:
                warnings.append(f"Low battery: {battery.percent}%")
            
            if not warnings:
                return "System health is good. All systems operating normally."
            else:
                return "System Health Warnings:\n" + "\n".join(f"- {w}" for w in warnings)
        except Exception as e:
            return f"Failed to check system health: {str(e)}"


