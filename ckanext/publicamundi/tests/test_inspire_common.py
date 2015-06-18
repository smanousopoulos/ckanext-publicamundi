import zope.interface
import zope.schema
import copy
import json
import datetime
from ckanext.publicamundi.tests.helpers import assert_faulty_keys
from ckanext.publicamundi.lib.metadata.types import *

#
# Responsible Party
#

# Fixtures 

# Schema validation errors, name, email not list
rp1 = ResponsibleParty(
    organization = "Non unicode name", 
    email = "non unicode email",
    role = "Author")

# Schema validation errors, empty fields
rp2 = ResponsibleParty(organization = u"org")

# Schema validation errors, email not correct
rp3 = ResponsibleParty(
    organization = u"unicode name",
    email = "unicodenon@email",
    role = u"author")

# No schema errors
rp_correct = ResponsibleParty(
    organization = u"org", 
    email = u"correct@email.com",
    role = "author")

# Tests 

def test_rp1():
    ''' Responsible Party validation errors, name, email not list'''
    assert_faulty_keys(rp1, expected_keys=set(['organization', 'email', 'role']))

def test_rp2():
    ''' Responsible Party validation errors, empty fields'''
    assert_faulty_keys(rp2, expected_keys=set(['email']))

def test_rp3():
    ''' Responsible Party validation errors, email not correct'''
    assert_faulty_keys(rp3, expected_keys=set(['email']))

def test_rp4():
    '''Responsible Party correct schema'''
    assert_faulty_keys(rp_correct, expected_keys=set([]))

#
# Conformity
#

# Fixtures

# Find schema validation errors date, creation, degree
cnf1 = Conformity(
    title = u"lala",
    date = 2015,
    date_type = "creationn",
    degree = "confofrmant")

# Validate correct schema
cnf_correct = Conformity(
    title = u"lala",
    date = datetime.date.today(),
    date_type = "creation",
    degree = "conformant")

# Tests

def test_cnf1():
    '''Conformity validation errors date, creation, degree'''
    assert_faulty_keys(cnf1, expected_keys=set(['date', 'date_type', 'degree']))

def test_cnf2():
    '''Conformity correct schema'''
    assert_faulty_keys(cnf_correct)

#
# Free keywords
#

# Fixtures


# Find schema validation errors: date_type
fkw1 = FreeKeyword(
    values = [u"val"],
    originating_vocabulary = u"Vocabulary",
    reference_date = datetime.date(800,1,1),
    date_type = "creationn")

# Find schema validation errors: values not list

fkw2 = FreeKeyword(
    values = u"val",
    originating_vocabulary = u"Vocabulary",
    reference_date = datetime.date(800,1,1),
    date_type = "creation")

# Find schema validation error - value not set
fkw3 = FreeKeyword(
    originating_vocabulary = u"Vocabulary",
    reference_date = datetime.date(800,1,1),
    date_type = "creation")

# Find schema validation invariant error - dates set without originating vocabulary
fkw4 = FreeKeyword(
    values = [u"val"],
    reference_date = datetime.date.today(),
    date_time = 'creation')

# Find schema validation invariant error - originating vocabulary without dates
fkw5 = FreeKeyword(
    values = [u"val"],
    originating_vocabulary = u"Vocabulary")

# Only value set - correct
fkw_correct = FreeKeyword(
    values = [u"val", u"val2"])

# Validate correct schema
fkw_correct_2 = FreeKeyword(
    values = [u"val"],
    originating_vocabulary = u"original",
    reference_date = datetime.date.today(),
    date_type = 'creation')

# Tests

def test_fkw1():
    '''Free Keywords validation errors: date_type'''
    assert_faulty_keys(fkw1,
        expected_keys=set(['date_type']))

def test_fkw2():
    '''Free Keywords validation errors: values not list'''
    assert_faulty_keys(fkw2,
        expected_keys=set(['values']))

def test_fkw3():
    '''Free Keywords validation errors: required values missing'''
    assert_faulty_keys(fkw3,
        expected_keys=set(['values']))

def test_fkw4():
    '''Free Keywords validation invariant error - not all fields set'''
    assert_faulty_keys(fkw4,
        expected_keys=set(['__after']), expected_invariants=["You need to fill in the rest free-keyword fields"])

def test_fkw5():
    '''Free Keywords validation invariant error - not all fields set'''
    assert_faulty_keys(fkw5,
        expected_keys=set(['__after']), expected_invariants=["You need to fill in the rest free-keyword fields"])

def test_fkw6():
    '''Free Keywords correct schema'''
    assert_faulty_keys(fkw_correct)

def test_fkw7():
    '''Free Keywords correct schema 2'''
    assert_faulty_keys(fkw_correct_2)


#
# Geographic BBox
#

# Fixtures

# Find schema validation errors: all not float
gbb1 = GeographicBoundingBox(
    nblat = 50, sblat = 50, wblng = 40, eblng= 30)

# Find schema validation errors - nblat, wblng greater than max allowed
gbb2 = GeographicBoundingBox(
    nblat = -1235.0, sblat = 0.0 , eblng = 123.123 , wblng = 1235.0)

# Find invariant errors (bad intervals)
gbb3 = GeographicBoundingBox(
    nblat = 30.0, sblat = 30.0 , eblng = -10.8 , wblng = 0.0)

# Validate correct schema
gbb4 = GeographicBoundingBox(
    nblat = 5.0, sblat = -10.12, wblng = 15.0, eblng = 19.0)

# Tests

def test_gbb1():
    '''GBBox validation errors: all not float'''
    assert_faulty_keys(gbb1, expected_keys=set(['nblat', 'sblat', 'eblng', 'wblng']))

def test_gbb2():
    '''GBBox validation errors - nblat, wblng greater than max allowed'''
    assert_faulty_keys(gbb2, expected_keys=set(['nblat', 'wblng']))

def test_gbb3():
    '''GBBox invariant errors - bad intervals'''
    assert_faulty_keys(gbb3, expected_keys=set(['__after']))

def test_gbb4():
    '''GBBox correct schema'''
    assert_faulty_keys(gbb4)

#
# Temporal Extent
#

# Fixtures

# Find schema validation errors: start missing
te1 = TemporalExtent(end = datetime.date.today())

# Find schema validation errors: start not date
te2 = TemporalExtent(
    start = 2015, end = datetime.date.today())

# Find schema invariant error - start date greater than end date
te3 = TemporalExtent(
    start = datetime.date(2555,01,01),end = datetime.date.today())

# Validate correct schema
te_correct = TemporalExtent(
    start = datetime.date.today(), end = datetime.date(2555,01,01))

# Tests

def test_te1():
    '''Temporal Extent validation errors: start not date'''
    assert_faulty_keys(te1, expected_keys=set(['start']))

def test_te2():
    '''Temporal Extent validation errors: start not date'''
    assert_faulty_keys(te2, expected_keys=set(['start']))

def test_te3():
    '''Temporal Extent invariant error - start date greater than end date'''
    assert_faulty_keys(te3, 
        expected_keys = set(['__after']), 
        expected_invariants = ["is later than end-date"])

def test_te4():
    '''Temporal Extent correct schema'''
    assert_faulty_keys(te_correct)

#
# Spatial Resolution
#

# Fixtures

# Find schema validation error - distance not int
sr1 = SpatialResolution(distance = 5.0, uom = u"lala")

# Find schema validation error for non-positive distance
sr2 = SpatialResolution(denominator = 2, distance = 0, uom=u"meters")

# Find invariant error - distance cannot be unitless
sr3 = SpatialResolution(distance = 5)

# Empty
sr4 = SpatialResolution()

# Validate correct schema
sr5 = SpatialResolution(denominator=200, distance = 5, uom = u"lala")
sr6 = SpatialResolution(denominator = 4000)

# Tests

def test_sr1():
    '''Spatial Resolution validation error - distance not int '''
    assert_faulty_keys(sr1, 
        expected_keys=set(['distance']))

def test_sr2():
    '''Spatial Resolution validation value 0'''
    assert_faulty_keys(sr2, expected_keys=['distance'])

def test_sr3():
    '''Spatial Resolution invariant error - not all values set'''
    assert_faulty_keys(sr3, 
        expected_keys=set(['__after']))

def test_sr4():
    '''Spatial Resolution invariant error - empty'''
    assert_faulty_keys(sr4, 
        expected_keys=set(['__after']))

def test_sr5():
    assert_faulty_keys(sr5)

def test_sr6():
    assert_faulty_keys(sr6)

#
# Reference system
#

# Fixtures

# Find reference system non-existing code
rs1 = ReferenceSystem(code='2100')

# Find reference system codespace and version provided
rs2 = ReferenceSystem(code='http://www.opengis.net/def/crs/EPSG/0/2100', code_space ='CustomSpace', version='5')

# Reference system correct
rs5 = ReferenceSystem(code='http://www.opengis.net/def/crs/EPSG/0/2100')

# Tests

def test_rs1():
    '''Reference system non-existing code error'''
    assert_faulty_keys(rs1,
        expected_keys=set(['code']))

def test_rs2():
    ''' Find reference system unicode version error'''
    assert_faulty_keys(rs2)
    assert rs2.code_space == 'CustomSpace'
    assert rs2.version == '5'

def test_rs_correct_2():
    '''Reference system correct schema '''
    assert_faulty_keys(rs5)

#
# Main 
#

if __name__ == '__main__':
    test_rp1()
    test_rp2()
    test_rp3()
    test_rp4()
