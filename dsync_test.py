import dsync
import json
link = dsync.translate("+[students]first_name|First,last_name|Last,middle_name|Gundogan,reg_number|20121815332,level|500,phone|456789,email|56789,gender|null,passport|23456,option|0,dob|425363,course_adviser|1,marital_status|Single,state_of_origin|1,nationality|59,address|null")
lister = [[0, 9], [7, 8]]
print(json.dumps(lister))
print (link)
