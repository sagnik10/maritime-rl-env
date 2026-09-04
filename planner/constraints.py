def apply_constraints(start,end):
    routes=[]

    suez=(30,32)
    panama=(9,-79)

    if start[1]<-20 and end[1]>20:
        routes=[start,panama,end]
    elif start[1]>20 and end[1]<80:
        routes=[start,suez,end]
    else:
        routes=[start,end]

    return routes
