# -*- coding: utf-8 -*-
"""
Created on Thu Mar  3 15:19:44 2022

@author: sofyg
"""
import geopandas as gpd
from terminus import termpicks_trace, termpicks_centerline, termpicks_interpolation

termpicks_df = gpd.read_file('TermPicks+CALFIN_V2.shp')
centerlines_df = gpd.read_file('termpicks_centerlines/termpicks_centerlines.shp')


trace_points = termpicks_trace(termpicks_df,2).trace2points(vert_dist = 30, truncate = True)
centerline_points = termpicks_centerline(centerlines_df,2).line2points(vert_dist= 30)


retreat = termpicks_interpolation(trace_points,centerline_points).calc_retreat()
mean_locations = termpicks_interpolation().mean_trace_loc()
