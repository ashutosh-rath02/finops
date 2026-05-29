from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class EmploymentType(str, Enum):
    salaried = "salaried"
    self_employed = "self_employed"
    business = "business"


class LoanType(str, Enum):
    personal_loan = "personal_loan"
    home_loan = "home_loan"
    business_loan = "business_loan"
    auto_loan = "auto_loan"


class Address(BaseModel):
    city: str
    state: str
    pin: str
    years_at_address: int


class Applicant(BaseModel):
    name: str
    date_of_birth: str
    pan: str
    mobile: str
    email: str
    address: Address


class LoanProduct(BaseModel):
    type: LoanType
    amount_requested: float
    currency: str = "INR"
    tenure_months: int
    purpose: str


class Employment(BaseModel):
    type: EmploymentType
    employer: Optional[str] = None
    designation: Optional[str] = None
    years_with_employer: Optional[float] = None
    monthly_gross_salary: Optional[float] = None
    monthly_net_salary: Optional[float] = None


class FinancialProfile(BaseModel):
    existing_emis: float
    declared_assets: float
    declared_liabilities: float


class LoanApplication(BaseModel):
    application_id: str
    submitted_at: datetime
    product: LoanProduct
    applicant: Applicant
    employment: Employment
    financials: FinancialProfile
    documents_provided: List[str]
