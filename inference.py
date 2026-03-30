import json 
 
def predict(input_data): 
    return {"status":"ok","message":"Maritime RL environment running"} 
 
if __name__=="__main__": 
    data={"input":"test"} 
    result=predict(data) 
    print(json.dumps(result)) 
