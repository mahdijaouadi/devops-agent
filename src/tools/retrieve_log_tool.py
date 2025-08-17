import json
import logging
from datetime import datetime
from typing import Annotated, Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

from google.cloud import logging_v2
from google.oauth2 import service_account
from google.api_core import exceptions as google_exceptions
from langgraph.prebuilt import InjectedState
import os
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LogSeverity(Enum):
    """GCP Log severity levels."""
    DEFAULT = "DEFAULT"
    DEBUG = "DEBUG"
    INFO = "INFO"
    NOTICE = "NOTICE"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    ALERT = "ALERT"
    EMERGENCY = "EMERGENCY"


@dataclass
class LogEntry:
    """Structured log entry data."""
    timestamp: datetime
    log_name: str
    severity: str
    text_payload: str
    resource: Dict[str, Any]
    insert_id: Optional[str] = None
    labels: Optional[Dict[str, str]] = None
    operation: Optional[Dict[str, Any]] = None
    source_location: Optional[Dict[str, Any]] = None
    span_id: Optional[str] = None
    trace: Optional[str] = None


@dataclass
class LogAnalysis:
    """Comprehensive log analysis results."""
    period: str
    total_entries: int
    severity_distribution: Dict[str, int]
    resources_distribution: Dict[str, float]
    raw_logs: str


class GCPLogRetriever:
    """Enhanced GCP Log Retriever with advanced analytics."""
    
    def __init__(self, credentials_info: Dict[str, Any]):
        """
        Initialize the log retriever.
        
        Args:
            credentials_info: Service account key information
        """
        self.credentials = service_account.Credentials.from_service_account_info(credentials_info)
        self.project_id = credentials_info['project_id']
        self.client = logging_v2.Client(project=self.project_id, credentials=self.credentials)
        
    def _parse_log_entry(self, entry) -> LogEntry:
        """Parse a GCP log entry into structured format."""
        try:
            return LogEntry(
                    timestamp=entry.timestamp,
                    log_name=entry.log_name,
                    severity=entry.severity,
                    text_payload=str(entry.payload) if entry.payload else "",
                    resource=entry.resource
            )
        except Exception as e:
            logger.warning(f"Failed to parse log entry: {e}")
            return None

    def _get_period_description(self, entries: List[LogEntry]) -> str:
        """Generate human-readable period description."""
        if not entries:
            return "No logs found for the specified period"
        
        if len(entries) == 1:
            return f"Single log entry at {entries[0].timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        
        start_time = entries[0].timestamp
        end_time = entries[-1].timestamp
        duration = end_time - start_time
        
        return (f"Logs from {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')} "
                f"to {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')} "
                f"(duration: {duration})")

    def _analyze_severity_distribution(self, entries: List[LogEntry]) -> Dict[str, int]:
        """Analyze severity distribution of log entries."""
        distribution = {}
        for entry in entries:
            severity = entry.severity
            distribution[severity] = distribution.get(severity, 0) + 1
        return distribution

    def _analyze_resources_distribution(self, entries: List[LogEntry]) -> Dict[str, float]:
        """Analyze resource distribution with percentages."""
        resources = {}
        total_entries = len(entries)
        
        if total_entries == 0:
            return {}
        
        for entry in entries:
            resource_key = json.dumps(entry.resource, sort_keys=True)
            resources[resource_key] = resources.get(resource_key, 0) + 1
        
        # Convert to percentages
        return {k: round((v / total_entries) * 100, 2) for k, v in resources.items()}


    def retrieve_logs(
        self,
        filter_string: str,
        max_entries: int = 100,
        order_by: str = "timestamp desc",
    ) -> LogAnalysis:
        """
        Retrieve and analyze logs from GCP.
        
        Args:
            filter_string: GCP log filter string
            max_entries: Maximum number of entries to retrieve
            order_by: Sort order for entries            
        Returns:
            LogAnalysis object with comprehensive analysis
        """
        try:
            logger.info(f"Executing log filter: {filter_string}")
            logger.info(f"Retrieving up to {max_entries} entries")
            
            # Retrieve logs
            entries_iterator = self.client.list_entries(
                filter_=filter_string,
                order_by=order_by,
                page_size=min(max_entries, 1000)  # GCP limit
            )
            
            # Parse entries
            entries = []
            for entry in entries_iterator:
                parsed_entry = self._parse_log_entry(entry)
                if parsed_entry:
                    entries.append(parsed_entry)
                if len(entries) >= max_entries:
                    break
            
            # Sort by timestamp (oldest first for analysis)
            entries.sort(key=lambda x: x.timestamp)
            
            logger.info(f"Retrieved {len(entries)} log entries")
            
            # Perform analysis
            severity_dist = self._analyze_severity_distribution(entries)
            resources_dist = self._analyze_resources_distribution(entries)
            
            # Generate raw logs
            raw_logs = "\n".join([
                f"{entry.text_payload}"
                for entry in entries
            ])            
            return LogAnalysis(
                period=self._get_period_description(entries),
                total_entries=len(entries),
                severity_distribution=severity_dist,
                resources_distribution=resources_dist,
                raw_logs=raw_logs
            )
            
        except google_exceptions.PermissionDenied:
            logger.error("Permission denied accessing GCP logs")
            raise Exception("Insufficient permissions to access GCP logs. Check service account permissions.")
        
        except google_exceptions.InvalidArgument as e:
            logger.error(f"Invalid filter argument: {e}")
            raise Exception(f"Invalid log filter: {e}")
        
        except Exception as e:
            logger.error(f"Unexpected error retrieving logs: {e}")
            raise Exception(f"Failed to retrieve logs: {e}")


def retrieve_logs(
    filter_string: str,
    state: Annotated[dict, InjectedState],
    max_entries: int = 100,
) -> Dict[str, Any]:
    """
    Retrieve and analyze logs from Google Cloud Platform (GCP) using a service account.

    This tool provides log retrieval capabilities from Google Cloud Platform
    Logging service, designed specifically to analyze and understand
    system issues more effectively.
    
    Args:
        filter_string: GCP log filter string (e.g., "resource.type=gce_instance severity>=ERROR")
        state: Automatically injected by the system - do not include this parameter in tool calls.
    Returns:
        dict: Log analysis results, including period, total_entries, severity_distribution, resources_distribution, and raw_logs. If an error occurs, returns a dict with error details.

    Example:
        >>> retrieve_logs(
        ...     filter_string='resource.type="gce_instance" severity>=ERROR',
        ... )

    Edge Cases:
        - If the filter string is invalid, returns an error with details.
        - If no logs match the filter, returns an empty analysis.
    """
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Validate inputs
        if not filter_string or not filter_string.strip():
            raise ValueError("Filter string cannot be empty")

        
        # Initialize retriever
        with open(os.path.abspath(os.path.join(current_dir, "..", "tmp", state["session_id"],"sa_key.json")), 'r') as f:
            sa_key = json.load(f)

        retriever = GCPLogRetriever(sa_key)
        # Retrieve and analyze logs
        analysis = retriever.retrieve_logs(
            filter_string=filter_string,
            max_entries=max_entries,
        )
        
        # Convert to dictionary for JSON serialization
        result = asdict(analysis)
        
        logger.info(f"Successfully retrieved and analyzed {analysis.total_entries} log entries")
        return result
        
    except Exception as e:
        logger.error(f"Error in retrieve_tool: {e}")
        return {
            'error': str(e),
            'period': 'Error occurred',
            'total_entries': 0,
            'severity_distribution': {},
            'resources_distribution': {},
            'raw_logs': '',
        }

