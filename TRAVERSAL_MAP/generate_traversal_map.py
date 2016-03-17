import System.Threading.Tasks as tasks
import rhinoscriptsyntax as rs
import math, time

#physical distance for sampling grid (in model units)
grid_dim = 24
#distance range to search for neighbors
search_dist = 10

#desired floor for traversal map creation
#suffix for layer selection from Rhino document
#TO DO - iterate through list of floors
flr = "3"

sample_pts = []

#layers to extract geometry from
obs_layers = ["bound_", "wall_int_", "column_"]
rm_layers = ["ws_cubicle_", "ws_standardprivateoffice_", "ws_projectroom_", "wall_int_", "am_"]

#arrays to hold extracted geometry
obs_crv = []
rm_crv = []

#extract obstacle geometry from layers (for view occlusion)
for lyr in obs_layers:
    #if rs.IsLayer(lyr):
    objs = rs.ObjectsByLayer(lyr+flr, rs.filter.curve)
    for obj in objs:
        obs_crv.append(obj)

#extract room geometry from layers (for point culling)
for lyr in rm_layers:
    #if rs.IsLayer(lyr):
    rms = rs.ObjectsByLayer(lyr+flr, rs.filter.curve)
    for rm in rms:
        if rs.IsCurveClosed(rm):
            rm_crv.append(rm)
            if rm not in obs_crv: obs_crv.append(rm)

#extract boundary geometry
bound_geo = rs.ObjectsByLayer("bound_"+flr)[0]

#find Z-height of floor
bound_z = rs.CurveAreaCentroid(bound_geo)[0][2]

#generate temporary surface for creation of sampling points
bound_srf = rs.AddPlanarSrf(bound_geo)

rs.UnselectAllObjects()

#measure dimensions of boundary surface
U_dim = rs.SurfaceDomain(bound_srf, 0)
V_dim = rs.SurfaceDomain(bound_srf, 1)

U_range = U_dim[1] - U_dim[0]
V_range = V_dim[1] - V_dim[0]

U_step = int(math.ceil(U_range / grid_dim))
V_step = int(math.ceil(V_range / grid_dim))

U_param = [U_dim[0] + x * U_range / U_step for x in range(U_step+1)]
V_param = [V_dim[0] + x * V_range / V_step for x in range(V_step+1)]

#instantiate point grid
for u in U_param:
    for v in V_param:
        #create point
        srf_pt = rs.SurfaceEvaluate(bound_srf, (u,v,0), 1)[0]

        #check if point is within floor boundary
        if rs.PointInPlanarClosedCurve(srf_pt, bound_geo):

            #cycle through rooms to see if point is inclusive and should be culled
            hits = 0
            for rm in rm_crv:
                if hits > 0: break
                if rs.PointInPlanarClosedCurve(srf_pt, rm): hits+= 1
            if hits > 0: continue
            else: sample_pts.append( srf_pt )

#remove temporary boundary surface
rs.DeleteObject( bound_srf )

#function to test which nearby sample pts visible from
#any given sample pt
#Note - parallel is non-working at the moment

def runChecks( pts, parallel ):
    if not pts: return

    results = range(len(pts))

    def checkVisible(pt):
        try:
            #scoring values
            neighbor = 0
            visible = 0

            idx = pts.index(pt)

            #iterate through sample points
            for test_pt in sample_pts:
                dist = rs.Distance(pt, test_pt)

                #check that point is not same as sample (dist == 0)
                #and that point is within search range
                if dist > 0 and dist < search_dist * grid_dim:
                    neighbor += 1

                    #generate curve for testing intersctions
                    test_crv = rs.AddCurve( (pt, test_pt) )
                    hits = 0

                    #iterate through obstacle curves to check for
                    #intersections
                    for ob in obs_crv:
                        if hits > 0: break
                        ob_cp = rs.CurveClosestPoint(ob, pt)
                        ob_pt = rs.EvaluateCurve(ob, ob_cp)
                        if rs.Distance(pt, ob_pt) < search_dist * grid_dim:
                            if rs.CurveCurveIntersection(test_crv, ob): hits += 1

                    #clear test crv
                    rs.DeleteObject( test_crv )

                    #check for intersections
                    if hits > 0: continue
                    else: visible += 1

            results[idx] = (visible / neighbor)

        except:
            pass

    if parallel:
        tasks.Parallel.ForEach(pts, checkVisible)
    else:
        for pt in pts: checkVisible(pt)

    return results

#timing for debug
start_time = time.time()
sample_val = runChecks( sample_pts, False )
end_time = time.time()

if not sample_val: print( "no results" )

min_val = min(sample_val)
max_val = max(sample_val)
val_range = max_val - min_val

print( "min: " + str(min_val) + " / max: " + str(max_val) + " / rng: " + str(val_range))

def makeMeshTile(pt, dim, color):
    h_dim = dim/2.0

    #define vertex positions
    bl = (pt[0] - h_dim, pt[1] - h_dim, bound_z)
    br = (pt[0] + h_dim, pt[1] - h_dim, bound_z)
    tr = (pt[0] + h_dim, pt[1] + h_dim, bound_z)
    tl = (pt[0] - h_dim, pt[1] + h_dim, bound_z)

    verts = rs.coerce3dpointlist( (bl,br,tr,tl) )

    #faces = [0, 1, 2, 3]
    #normals = [(0,0,1), (0,0,1), (0,0,1), (0,0,1)]
    colors = [color, color, color, color]
    #rs.AddMesh(verts, faces)
    srf = rs.AddSrfPt(verts)
    rs.ObjectColor(srf, color)


for i in range( len(sample_pts) ):
    val = (sample_val[i] - min_val) / val_range

    #if val < 0.5:
        #temp_val = val * 2
        #color = (255, 255*temp_val, 0)
    #elif val == 0.5:
        #color = (255, 255, 0)
    #else:
        #temp_val = (val - 0.5) * 2
        #color = (255 - temp_val*255, 255 - temp_val*127, 0)

    #newPt = rs.AddPoint( sample_pts[i] )
    color = ( 255 - int(255*val), 0, 0)
    #rs.ObjectColor( newPt, color )

    makeMeshTile( sample_pts[i], grid_dim, color )

print(" runtime : "+ str(end_time - start_time) )
