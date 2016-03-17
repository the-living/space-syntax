import rhinoscriptsyntax as rs
import math

#floor suffixes - used to reference Rhino geometry by layer
floors = ["_02", "_02m", "_03"]

#extract Rhino layer names to list of strings
layers = rs.LayerNames()

#scoring containers
overall_score = []
overall_max = []

#iterate through floors
for floor in floors:

    #check if required layer exists before proceeding
    if "CIRC"+floor in layers:

        #create list of sample tile (pixel) geometry
        circ_grid = rs.ObjectsByLayer("CIRC"+floor)
        #extract value from sample tile (pixel)
        circ_val = [ (255-rs.ObjectColor(srf).R)/255 for srf in circ_grid ]
        #create boundary polygons of pixel for intersection tests
        circ_crv = [rs.CloseCurve(rs.JoinCurves(rs.DuplicateEdgeCurves(srf), True)) for srf in circ_grid ]
        #find pixel location for distance checks
        circ_centroid = [rs.CurveAreaCentroid(crv)[0] for crv in circ_crv]

        #create list of path geometry (series of curves from adjacency shortest paths)
        path_lines = rs.ObjectsByLayer("PATHS"+floor)

        #create score array for each path segment
        scores = [ [] for i in range(len(path_lines)) ]

        #iterate through each path segment
        for path in path_lines:

            #check length of path segment (for limiting checks)
            path_len = rs.CurveLength(path)

            #path segment midpoint (for measuring to eval pts)
            path_midPt = rs.CurveMidPoint(path)

            #path index for scoring coordination
            idx = path_lines.index(path)

            #iterate through pixels
            for i in range(len( circ_centroid )):
                #find pixels within intersection range
                if rs.Distance(path_midPt, circ_centroid[i]) <= path_len/2:
                    #check if path intersects with pixel boundary curve
                    if rs.CurveCurveIntersection(path, circ_crv[i]):
                        #add value of intersected pixel to scoring array
                        scores[idx].append(circ_val[i])

        #SCORING
        #score display in Rhino commandline
        print "Floor " + floor[1:]

        sum_score = 0
        max_score = 0

        for score in scores:
            max_score += len(score)
            sum_score += sum(score)

        overall_score.append( sum_score )
        overall_max.append( max_score )

        print (sum_score/max_score) * 10


        #clean up excess rhino geometry
        rs.DeleteObjects(circ_crv)

    else:
        print "Floor " + floor[1:] + " not in model"

#print overall_score
#print overall_max
print "Overall score: " + str(10*sum(overall_score)/sum(overall_max))
