"""
Database models and query builders
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, date
from decimal import Decimal
from .client import DataAPIClient
class BaseModel:
    """Base class for database models"""
    
    table_name = None
    
    def __init__(self, db: DataAPIClient):
        self.db = db
        if not self.table_name:
            raise ValueError("table_name must be defined")
    
    def find_by_id(self, id: Any) -> Optional[Dict]:
        """Find a record by ID"""
        sql = f"SELECT * FROM {self.table_name} WHERE id = :id::uuid"
        return self.db.query_one(sql, [{'name': 'id', 'value': {'stringValue': str(id)}}])
    
    def find_all(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Find all records with pagination"""
        sql = f"SELECT * FROM {self.table_name} LIMIT :limit OFFSET :offset"
        params = [
            {'name': 'limit', 'value': {'longValue': limit}},
            {'name': 'offset', 'value': {'longValue': offset}}
        ]
        return self.db.query(sql, params)
    
    def create(self, data: Dict, returning: str = 'id') -> str:
        """Create a new record"""
        return self.db.insert(self.table_name, data, returning=returning)
    
    def update(self, id: Any, data: Dict) -> int:
        """Update a record by ID"""
        return self.db.update(self.table_name, data, "id = :id::uuid", {'id': str(id)})
    
    def delete(self, id: Any) -> int:
        """Delete a record by ID"""
        return self.db.delete(self.table_name, "id = :id::uuid", {'id': str(id)})


class Users(BaseModel):
    """Users table operations"""
    table_name = 'users'
    
    def find_by_clerk_id(self, clerk_user_id: str) -> Optional[Dict]:
        """Find user by Clerk ID"""
        sql = f"SELECT * FROM {self.table_name} WHERE clerk_user_id = :clerk_id"
        params = [{'name': 'clerk_id', 'value': {'stringValue': clerk_user_id}}]
        return self.db.query_one(sql, params)
    
    def create_user(self, clerk_user_id: str, display_name: str = None, 
                   email: str = None) -> str:
        """Create a new user"""
        data = {
            'clerk_user_id': clerk_user_id,
            'display_name': display_name,
            'email': email
        }
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}
        return self.db.insert(self.table_name, data, returning='clerk_user_id')



class ActivityHistory(BaseModel):
    """Account Activity History table"""
    table_name = 'activity_history'
    
    def find_by_user(self, clerk_user_id: str) -> List[Dict]:
        """Find all activity_history for a user"""
        sql = f"""
            SELECT * FROM {self.table_name} 
            WHERE clerk_user_id = :user_id 
            ORDER BY created_at DESC
        """
        params = [{'name': 'user_id', 'value': {'stringValue': clerk_user_id}}]
        return self.db.query(sql, params)

    
    def create_activity_history(
        self,
        clerk_user_id: str,
        account_name: str,
        email: str = None,
        details: str = None,
        label: str = None,
        activity_type: str = None,
        activity_date: str = None,
    ) -> str:
        """Insert a row into activity_history."""
        data = {
            'clerk_user_id': clerk_user_id,
            'account_name': account_name,
            'email': email,
            'details': details,
            'label': label,
            'activity_type': activity_type,
            'activity_date': activity_date,
        }
        data = {k: v for k, v in data.items() if v is not None}
        return self.db.insert(self.table_name, data, returning='id')



class Jobs(BaseModel):
    """Jobs table operations"""
    table_name = 'jobs'
    
    def create_job(self, clerk_user_id: str, job_type: str, 
                  request_payload: Dict = None) -> str:
        """Create a new job"""
        data = {
            'clerk_user_id': clerk_user_id,
            'job_type': job_type,
            'status': 'pending',
            'request_payload': request_payload
        }
        return self.db.insert(self.table_name, data, returning='id')
    
    def update_status(self, job_id: str, status: str, error_message: str = None) -> int:
        """Update job status"""
        data = {'status': status}
        
        if status == 'running':
            data['started_at'] = datetime.utcnow()
        elif status in ['completed', 'failed']:
            data['completed_at'] = datetime.utcnow()
        
        if error_message:
            data['error_message'] = error_message
        
        return self.db.update(self.table_name, data, "id = :id::uuid", {'id': job_id})
    
    def update_report(self, job_id: str, report_payload: Dict) -> int:
        """Update job with Reporter agent's analysis"""
        data = {'report_payload': report_payload}
        return self.db.update(self.table_name, data, "id = :id::uuid", {'id': job_id})
    
    def update_charts(self, job_id: str, charts_payload: Dict) -> int:
        """Update job with Charter agent's visualization data"""
        data = {'charts_payload': charts_payload}
        return self.db.update(self.table_name, data, "id = :id::uuid", {'id': job_id})
    
    def update_retirement(self, job_id: str, retirement_payload: Dict) -> int:
        """Update job with Retirement agent's projections"""
        data = {'retirement_payload': retirement_payload}
        return self.db.update(self.table_name, data, "id = :id::uuid", {'id': job_id})
    
    def update_summary(self, job_id: str, summary_payload: Dict) -> int:
        """Update job with Planner's final summary"""
        data = {'summary_payload': summary_payload}
        return self.db.update(self.table_name, data, "id = :id::uuid", {'id': job_id})
    
    def find_by_user(self, clerk_user_id: str, status: str = None, 
                    limit: int = 20) -> List[Dict]:
        """Find jobs for a user"""
        if status:
            sql = f"""
                SELECT * FROM {self.table_name}
                WHERE clerk_user_id = :user_id AND status = :status
                ORDER BY created_at DESC
                LIMIT :limit
            """
            params = [
                {'name': 'user_id', 'value': {'stringValue': clerk_user_id}},
                {'name': 'status', 'value': {'stringValue': status}},
                {'name': 'limit', 'value': {'longValue': limit}}
            ]
        else:
            sql = f"""
                SELECT * FROM {self.table_name}
                WHERE clerk_user_id = :user_id
                ORDER BY created_at DESC
                LIMIT :limit
            """
            params = [
                {'name': 'user_id', 'value': {'stringValue': clerk_user_id}},
                {'name': 'limit', 'value': {'longValue': limit}}
            ]
        
        return self.db.query(sql, params)


class Database:
    """Main database interface providing access to all models"""
    
    def __init__(self, cluster_arn: str = None, secret_arn: str = None,
                 database: str = None, region: str = None):
        """Initialize database with all model classes"""
        self.client = DataAPIClient(cluster_arn, secret_arn, database, region)
        
        # Initialize all models
        self.users = Users(self.client)
        self.activity_history = ActivityHistory(self.client)
        self.jobs = Jobs(self.client)
    
    def execute_raw(self, sql: str, parameters: List[Dict] = None) -> Dict:
        """Execute raw SQL for complex queries"""
        return self.client.execute(sql, parameters)
    
    def query_raw(self, sql: str, parameters: List[Dict] = None) -> List[Dict]:
        """Execute raw SELECT query"""
        return self.client.query(sql, parameters)