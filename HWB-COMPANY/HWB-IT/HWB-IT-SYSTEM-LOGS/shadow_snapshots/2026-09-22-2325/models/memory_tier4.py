from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime

class Tier4Model(BaseModel):
    """Base class for Tier 4 Structured Operational Memory models."""
    pass

class LeadModel(Tier4Model):
    id: Optional[int] = None
    job_title: Optional[str] = None
    center_name: Optional[str] = None
    email: Optional[str] = None
    wage: Optional[float] = None
    cleaning_hours: Optional[float] = None
    calculated_waste: Optional[float] = None
    timestamp: Optional[date] = None
    process_id: str = "MKT-001"
    phone: Optional[str] = None
    address: Optional[str] = None
    county: Optional[str] = None
    zipcode: Optional[str] = None
    director: Optional[str] = None
    capacity: Optional[int] = None
    city: Optional[str] = None
    state: Optional[str] = None
    industry: Optional[str] = None
    sqf: Optional[int] = None
    input_date: Optional[date] = None
    status: str = "New"
    is_converted: bool = False
    owner_id: Optional[int] = None
    preferred_date: Optional[str] = None
    preferred_time: Optional[str] = None
    lead_source: Optional[str] = None
    service_interest: Optional[str] = None
    priority_level: Optional[str] = None
    facility_type: Optional[str] = None
    budget_range: Optional[str] = None
    next_action_date: Optional[str] = None
    estimated_annual_value: Optional[float] = None
    last_contacted_by: Optional[str] = None
    traffic_cycle: Optional[str] = None
    decision_maker: Optional[str] = None
    notes: Optional[str] = None
    updated_at: Optional[date] = None

class CustomerModel(Tier4Model):
    customer_id: Optional[int] = None
    company_name: str
    contact_person_name: Optional[str] = None
    company_address: str
    city: Optional[str] = None
    zip: Optional[str] = None
    state: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    quote_number: Optional[str] = None
    contract_period: Optional[str] = None
    frequency: Optional[str] = None
    start_date: Optional[date] = None
    start_time: Optional[str] = None
    payment_terms: Optional[str] = None
    website: Optional[str] = None
    billing_address: Optional[str] = None
    annual_revenue: float = 0.0
    assigned_rep_id: Optional[int] = None
    notes: Optional[str] = None
    created_at: Optional[date] = None
    status: str = "Active"
    sqf: int = 0
    traffic_cycle: Optional[str] = None

class OpportunityModel(Tier4Model):
    opp_id: Optional[int] = None
    account_id: Optional[int] = None
    stage: Optional[str] = "Discovery"
    amount: Optional[float] = 0.0
    expected_close: Optional[date] = None
    probability: int = 10
    last_modified: Optional[date] = None

class MilestoneModel(Tier4Model):
    id: Optional[int] = None
    category: str
    name: str
    status: str = "pending"
    description: Optional[str] = None
