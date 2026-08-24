"""Intent definitions for inbound TrafficSMS messages."""

from enum import Enum


class SMSIntent(str, Enum):
    """Commands supported by the TrafficSMS SMS engine."""

    UNKNOWN = "unknown"
    HELP = "help"
    START = "start"
    STOP = "stop"
    TRAFFIC = "traffic"
    TRAFFIC_HOME = "traffic_home"
    TRAFFIC_WORK = "traffic_work"
    TRAFFIC_GYM = "traffic_gym"
    TRAFFIC_SCHOOL = "traffic_school"
    TRAFFIC_ROUTE = "traffic_route"
    TRAFFIC_SAVED_ROUTE = "traffic_saved_route"
    SAVE_ROUTE = "save_route"
    LIST_ROUTES = "list_routes"
    DELETE_ROUTE = "delete_route"
    SUBSCRIBE = "subscribe"
    POLICE_REPORT = "police_report"
    POLICE_VOTE = "police_vote"
