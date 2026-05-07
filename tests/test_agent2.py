# test_agent2.py
import sys
sys.path.insert(0, '.')
import agents.agent2 as agent2
from models.dynamic_record import DynamicRecord

record = DynamicRecord(
    data={"Make_model": "BMW", "Fuel": "Benzyna"},
    row_index=0
)

results = agent2.analyze_batch([record])
print(type(results))
print(results)