
import pytest
from nexor_x.operations.probation_exposure_ramp import ProbationExposureRamp

def test_full_outside_probation():
    assert ProbationExposureRamp().multiplier(probation={"active": False}) == 1.0

def test_first_25():
    assert ProbationExposureRamp().multiplier(probation={"active": True, "admitted_entries": 0}) == 0.25

def test_second_50():
    assert ProbationExposureRamp().multiplier(probation={"active": True, "admitted_entries": 1}) == 0.50

def test_third_75():
    assert ProbationExposureRamp().multiplier(probation={"active": True, "admitted_entries": 2}) == 0.75

def test_reduce_only_full():
    assert ProbationExposureRamp().multiplier(probation={"active": True}, reduce_only=True) == 1.0

def test_scale_quantity():
    assert ProbationExposureRamp.scale_quantity(4, 0.25) == 1.0

def test_invalid_quantity():
    with pytest.raises((ValueError, TypeError)):
        ProbationExposureRamp.scale_quantity("abc", 0.25)
