"""
GlucoShield Physiology Engine Package
=====================================
Mechanistic metabolic Digital Twin modeling glucose, insulin pharmacokinetics,
and carbohydrate gastrointestinal absorption.
"""

from physiology.state import MetabolicState
from physiology.parameters import PhysiologicalParameters
from physiology.constraints import PARAMETER_BOUNDS, clamp_parameters, enforce_state_constraints
from physiology.compartments import compute_metabolic_derivatives
from physiology.integrator import RK4Integrator, rk4_microstep
