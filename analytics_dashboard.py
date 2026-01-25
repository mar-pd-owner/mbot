"""
Real-time Analytics Dashboard for MBOT
Monitors all activities and provides insights
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # For non-GUI environments
import io
import base64
from collections import defaultdict

class AnalyticsDashboard:
    def __init__(self):
        self.data_file = 'analytics_data.json'
        self.realtime_data = {
            'user_activity': defaultdict(list),
            'boost_activity': defaultdict(list),
            'system_performance': defaultdict(list),
            'error_logs': [],
            'user_growth': []
        }
        
        # Load existing data
        self.load_data()
        
        # Start background updater
        self.running = True
        import threading
        self.updater_thread = threading.Thread(target=self.background_updater)
        self.updater_thread.daemon = True
        self.updater_thread.start()
    
    def load_data(self):
        """Load analytics data from file"""
        try:
            with open(self.data_file, 'r') as f:
                self.realtime_data = json.load(f)
        except:
            self.realtime_data = {
                'user_activity': {},
                'boost_activity': {},
                'system_performance': {},
                'error_logs': [],
                'user_growth': []
            }
    
    def save_data(self):
        """Save analytics data to file"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.realtime_data, f, indent=2)
        except Exception as e:
            print(f"Error saving analytics data: {e}")
    
    def background_updater(self):
        """Background thread to update and save data"""
        while self.running:
            time.sleep(60)  # Update every minute
            self.cleanup_old_data()
            self.save_data()
    
    def log_user_activity(self, user_id: int, activity_type: str, details: Dict = None):
        """Log user activity"""
        timestamp = datetime.now().isoformat()
        entry = {
            'timestamp': timestamp,
            'activity_type': activity_type,
            'details': details or {},
            'user_id': user_id
        }
        
        # Add to realtime data
        date_key = datetime.now().strftime("%Y-%m-%d")
        if date_key not in self.realtime_data['user_activity']:
            self.realtime_data['user_activity'][date_key] = []
        
        self.realtime_data['user_activity'][date_key].append(entry)
        
        # Update user growth
        self.update_user_growth()
    
    def log_boost_activity(self, video_id: str, boost_type: str, count: int, success: bool):
        """Log boost activity"""
        timestamp = datetime.now().isoformat()
        entry = {
            'timestamp': timestamp,
            'video_id': video_id,
            'boost_type': boost_type,
            'count': count,
            'success': success
        }
        
        # Add to realtime data
        hour_key = datetime.now().strftime("%Y-%m-%d %H:00")
        if hour_key not in self.realtime_data['boost_activity']:
            self.realtime_data['boost_activity'][hour_key] = []
        
        self.realtime_data['boost_activity'][hour_key].append(entry)
    
    def log_system_performance(self, metric: str, value: float):
        """Log system performance metrics"""
        timestamp = datetime.now().isoformat()
        entry = {
            'timestamp': timestamp,
            'metric': metric,
            'value': value
        }
        
        # Add to realtime data
        if metric not in self.realtime_data['system_performance']:
            self.realtime_data['system_performance'][metric] = []
        
        self.realtime_data['system_performance'][metric].append(entry)
        
        # Keep only last 1000 entries per metric
        if len(self.realtime_data['system_performance'][metric]) > 1000:
            self.realtime_data['system_performance'][metric] = self.realtime_data['system_performance'][metric][-1000:]
    
    def log_error(self, error_type: str, message: str, details: Dict = None):
        """Log error"""
        timestamp = datetime.now().isoformat()
        entry = {
            'timestamp': timestamp,
            'error_type': error_type,
            'message': message,
            'details': details or {}
        }
        
        self.realtime_data['error_logs'].append(entry)
        
        # Keep only last 500 errors
        if len(self.realtime_data['error_logs']) > 500:
            self.realtime_data['error_logs'] = self.realtime_data['error_logs'][-500:]
    
    def update_user_growth(self):
        """Update user growth statistics"""
        try:
            with open('user_data.json', 'r') as f:
                user_data = json.load(f)
            
            timestamp = datetime.now().isoformat()
            total_users = len(user_data)
            
            entry = {
                'timestamp': timestamp,
                'total_users': total_users
            }
            
            self.realtime_data['user_growth'].append(entry)
            
            # Keep only last 365 days
            if len(self.realtime_data['user_growth']) > 365:
                self.realtime_data['user_growth'] = self.realtime_data['user_growth'][-365:]
                
        except:
            pass
    
    def get_daily_report(self, date_str: Optional[str] = None) -> Dict:
        """Get daily analytics report"""
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        report = {
            'date': date_str,
            'user_activity': 0,
            'boost_activity': 0,
            'total_boosts': 0,
            'successful_boosts': 0,
            'failed_boosts': 0,
            'unique_users': set(),
            'peak_rps': 0,
            'average_response_time': 0,
            'error_count': 0
        }
        
        # Analyze user activity
        if date_str in self.realtime_data['user_activity']:
            activities = self.realtime_data['user_activity'][date_str]
            report['user_activity'] = len(activities)
            report['unique_users'] = len(set(act['user_id'] for act in activities))
        
        # Analyze boost activity
        for hour_key, boosts in self.realtime_data['boost_activity'].items():
            if hour_key.startswith(date_str):
                report['boost_activity'] += len(boosts)
                for boost in boosts:
                    report['total_boosts'] += boost['count']
                    if boost['success']:
                        report['successful_boosts'] += boost['count']
                    else:
                        report['failed_boosts'] += boost['count']
        
        # Analyze system performance
        if 'rps' in self.realtime_data['system_performance']:
            rps_values = [entry['value'] for entry in self.realtime_data['system_performance']['rps'] 
                         if entry['timestamp'].startswith(date_str)]
            if rps_values:
                report['peak_rps'] = max(rps_values)
        
        if 'response_time' in self.realtime_data['system_performance']:
            rt_values = [entry['value'] for entry in self.realtime_data['system_performance']['response_time']
                        if entry['timestamp'].startswith(date_str)]
            if rt_values:
                report['average_response_time'] = sum(rt_values) / len(rt_values)
        
        # Count errors
        report['error_count'] = len([error for error in self.realtime_data['error_logs']
                                    if error['timestamp'].startswith(date_str)])
        
        return report
    
    def get_user_analytics(self, user_id: int) -> Dict:
        """Get analytics for specific user"""
        user_activities = []
        
        for date_key, activities in self.realtime_data['user_activity'].items():
            for activity in activities:
                if activity['user_id'] == user_id:
                    user_activities.append(activity)
        
        # Calculate statistics
        total_activities = len(user_activities)
        activity_types = defaultdict(int)
        boost_counts = defaultdict(int)
        
        for activity in user_activities:
            activity_type = activity['activity_type']
            activity_types[activity_type] += 1
            
            if activity_type == 'boost':
                details = activity.get('details', {})
                boost_counts[details.get('video_id', 'unknown')] = boost_counts.get(
                    details.get('video_id', 'unknown'), 0) + details.get('count', 1)
        
        # Find most active days
        day_activity = defaultdict(int)
        for activity in user_activities:
            day = activity['timestamp'][:10]
            day_activity[day] += 1
        
        most_active_day = max(day_activity.items(), key=lambda x: x[1]) if day_activity else ("None", 0)
        
        return {
            'user_id': user_id,
            'total_activities': total_activities,
            'activity_breakdown': dict(activity_types),
            'boost_breakdown': dict(boost_counts),
            'most_active_day': {
                'date': most_active_day[0],
                'activities': most_active_day[1]
            },
            'first_activity': user_activities[0]['timestamp'] if user_activities else None,
            'last_activity': user_activities[-1]['timestamp'] if user_activities else None
        }
    
    def generate_chart(self, chart_type: str, days: int = 7) -> str:
        """Generate chart image and return as base64"""
        try:
            plt.figure(figsize=(10, 6))
            
            if chart_type == 'user_growth':
                # Get user growth data
                growth_data = self.realtime_data['user_growth'][-days*24:]
                dates = [entry['timestamp'][:10] for entry in growth_data]
                counts = [entry['total_users'] for entry in growth_data]
                
                plt.plot(dates, counts, marker='o', linewidth=2, markersize=6)
                plt.title(f'User Growth (Last {days} Days)')
                plt.xlabel('Date')
                plt.ylabel('Total Users')
                plt.xticks(rotation=45)
                plt.grid(True, alpha=0.3)
            
            elif chart_type == 'boost_activity':
                # Get boost activity data
                today = datetime.now()
                date_range = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]
                date_range.reverse()
                
                daily_boosts = []
                for date in date_range:
                    total = 0
                    for hour_key, boosts in self.realtime_data['boost_activity'].items():
                        if hour_key.startswith(date):
                            total += sum(boost['count'] for boost in boosts)
                    daily_boosts.append(total)
                
                plt.bar(date_range, daily_boosts, color='skyblue')
                plt.title(f'Daily Boost Activity (Last {days} Days)')
                plt.xlabel('Date')
                plt.ylabel('Number of Boosts')
                plt.xticks(rotation=45)
                plt.grid(True, alpha=0.3, axis='y')
            
            elif chart_type == 'system_performance':
                # Get RPS data
                if 'rps' in self.realtime_data['system_performance']:
                    rps_data = self.realtime_data['system_performance']['rps'][-days*24:]
                    timestamps = [entry['timestamp'][11:16] for entry in rps_data[-24:]]
                    values = [entry['value'] for entry in rps_data[-24:]]
                    
                    plt.plot(timestamps, values, marker='s', linewidth=2, markersize=4, color='green')
                    plt.title('Requests Per Second (Last 24 Hours)')
                    plt.xlabel('Time')
                    plt.ylabel('RPS')
                    plt.xticks(rotation=45)
                    plt.grid(True, alpha=0.3)
                    plt.fill_between(timestamps, values, alpha=0.3, color='green')
            
            plt.tight_layout()
            
            # Save to buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            
            # Convert to base64
            img_str = base64.b64encode(buf.read()).decode()
            plt.close()
            
            return img_str
            
        except Exception as e:
            print(f"Error generating chart: {e}")
            return ""
    
    def get_system_health(self) -> Dict:
        """Get system health status"""
        # Analyze last hour
        one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
        
        recent_errors = [error for error in self.realtime_data['error_logs']
                        if error['timestamp'] > one_hour_ago]
        
        # Calculate error rate
        total_activities = 0
        for date_key, activities in self.realtime_data['user_activity'].items():
            for activity in activities:
                if activity['timestamp'] > one_hour_ago:
                    total_activities += 1
        
        error_rate = (len(recent_errors) / max(total_activities, 1)) * 100
        
        # Check performance metrics
        if 'rps' in self.realtime_data['system_performance']:
            recent_rps = [entry['value'] for entry in self.realtime_data['system_performance']['rps']
                         if entry['timestamp'] > one_hour_ago]
            avg_rps = sum(recent_rps) / len(recent_rps) if recent_rps else 0
        else:
            avg_rps = 0
        
        # Determine health status
        if error_rate < 5 and avg_rps > 10:
            health_status = "healthy"
        elif error_rate < 10:
            health_status = "warning"
        else:
            health_status = "critical"
        
        return {
            'health_status': health_status,
            'error_rate': round(error_rate, 2),
            'avg_rps': round(avg_rps, 2),
            'recent_errors': len(recent_errors),
            'timestamp': datetime.now().isoformat()
        }
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old analytics data"""
        cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).strftime("%Y-%m-%d")
        
        # Clean user activity
        keys_to_remove = []
        for date_key in self.realtime_data['user_activity'].keys():
            if date_key < cutoff_date:
                keys_to_remove.append(date_key)
        
        for key in keys_to_remove:
            del self.realtime_data['user_activity'][key]
        
        # Clean boost activity
        keys_to_remove = []
        for hour_key in self.realtime_data['boost_activity'].keys():
            if hour_key[:10] < cutoff_date:
                keys_to_remove.append(hour_key)
        
        for key in keys_to_remove:
            del self.realtime_data['boost_activity'][key]
        
        # Clean old errors (keep last 500 only)
        if len(self.realtime_data['error_logs']) > 500:
            self.realtime_data['error_logs'] = self.realtime_data['error_logs'][-500:]
    
    def export_data(self, format_type: str = 'json') -> str:
        """Export analytics data"""
        if format_type == 'json':
            return json.dumps(self.realtime_data, indent=2)
        elif format_type == 'csv':
            # Convert to CSV format
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(['Type', 'Timestamp', 'Details'])
            
            # Write data
            for date_key, activities in self.realtime_data['user_activity'].items():
                for activity in activities:
                    writer.writerow([
                        'user_activity',
                        activity['timestamp'],
                        json.dumps(activity)
                    ])
            
            return output.getvalue()
        
        return ""

# Global instance
analytics = AnalyticsDashboard()
