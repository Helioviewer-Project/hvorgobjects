#
# Generates the positions of planets as seen from the Earth
#
# Allows us to label planets in the LASCO C2, C3 field of view
# for example, 2000/05/15 11:18
# See http://sci.esa.int/soho/18976-lasco-c3-image-showing-the-positions-of-the-planets/
# 
#
import json
import os
from copy import deepcopy

import numpy as np

from astropy.coordinates import get_body
from astropy.time import Time
import astropy.units as u
from astropy.constants import c
from astropy.coordinates import SkyCoord

from sunpy.coordinates import frames

# Where to store the data
directory = os.path.expanduser('~/hvp/hvorgobjects/output/json')

# Bodies
body_names = ('mercury', 'venus', 'jupiter', 'saturn', 'uranus', 'neptune')

# Days we want to calculate positions for
# transit_of_venus_2012 = Time('2012-06-05 00:00:00')
# n_days = 2

#multiple_planets = Time('2000-05-01 00:00:00')
#n_days = 28

try_a_year = Time('2000-05-11 00:00:00')
n_days = 1

# Which times?
initial_time = try_a_year

# Time step
dt = 30*u.minute

# duration
duration = 1 * u.day

# Where are we looking from - the observer
observer_name = 'earth'

# Write a file only when the bisy has an angular separation from the Sun
# less than the maximum below
maximum_angular_separation = 10 * u.deg

# Format the output time as requested.
def format_time_output(t):
    """
    Format the time output.

    Parameters
    ----------
    t : `~astropy.time.Time`
        The time that is to be formatted.

    Returns
    -------
    format_time_output
        The input time in the requested format.

    """
    # Returns as an integer number of seconds
    return int(np.rint(t.unix * 1000))


def file_name_format(observer_name, body_name, t, file_type='json'):
    """
    The file name format that has been decided upon for the output.

    Parameters
    ----------
    observer_name : `~str`
        The name of the observer.

    body_name : `~str`
        The body that is observed.

    t : `~astropy.time.Time`
        A time that signifies the time range of information in the file.

    file_type : '~str`
        The file type that will be written.

    Returns
    -------
    file_name_format
        The filename in the requested format
    """
    tc = deepcopy(t)
    tc.out_subfmt = 'date'
    return '{:s}_{:s}_{:s}.{:s}'.format(observer_name, body_name, str(tc), file_type)


def distance_format(d, scale=1*u.au):
    """
    Returns the distances in the requested format

    Parameters
    ----------
    d : `~astropy.unit`
        A distance in units convertible to kilometers.

    scale : `~astropy.unit`
        The scale the input unit is measured in.

    Returns
    -------
    distance_format : `~float`
        A floating point number that is implicitly measured in the input scale.
    """
    return (d / scale).decompose().value


def distance_between_locations_hcc(o1_hcc, o2_hcc):
    return (np.sqrt((o2_hcc.x - o1_hcc.x)**2 + (o2_hcc.y - o1_hcc.y)**2 + (o2_hcc.z - o1_hcc.z)**2)).to(u.m)


def distance_between_locations(object1, object2):
    o1_hcc = object1.transform_to(frames.Heliocentric)
    o2_hcc = object2.transform_to(frames.Heliocentric)
    return distance_between_locations_hcc(o1_hcc, o2_hcc)


# Go through each of the bodies
for body_name in body_names:

    # Pick the next start time at the observer
    for n in range(0, n_days):
        start_time = initial_time + n*u.day

        # Reset the positions directory for the new start time
        positions = dict()
        positions[observer_name] = dict()
        positions[observer_name][body_name] = dict()

        # Reset the counter to the new start time
        t = start_time

        # Information to screen
        print('Body = {:s}, day = {:s}'.format(body_name, str(t)))

        # If True, then the day contains at least one
        # valid position
        save_file_for_this_duration = False

        # Calculate the positions in the duration
        while t - start_time < duration:
            # The location of the observer
            observer_location = get_body('earth', t) #.transform_to(frames.HeliographicStonyhurst)
            # Shift the observer out to approximate location of SOHO.
            # TODO understand LASCO and helioviewer image processing steps
            #observer_location = SkyCoord(lon=earth_location.lon,
            #                             lat=earth_location.lat,
            #                             radius=1*u.au,
            #                             obstime=t,
            #                             frame=frames.HeliographicStonyhurst)

            # The location of the body
            this_body = get_body(body_name, t)

            # The position of the body as seen from the observer location
            position = this_body.transform_to(observer_location).transform_to(frames.Helioprojective)

            # Transform to Helioprojective
            #position = position.transform_to(frames.Helioprojective)
            
            # Position of the Sun as seen by the observer
            sun_position = get_body('sun', t).transform_to(observer_location)

            # Angular distance of the body from the Sun
            angular_separation = sun_position.separation(position)
            print(np.abs(angular_separation))

            # We only want to write out data when the body is close
            # to the Sun.  This will reduce the number and size of
            # files that we have to store.
            if np.abs(angular_separation) <= maximum_angular_separation:
                # Valid position, so set the flag
                save_file_for_this_duration = True

                # Information to screen
                print('Body = {:s}, angular separation = {:s} degrees'.format(body_name, str(angular_separation.value)))

                # location of the body in HCC
                body_hcc = this_body.transform_to(frames.Heliocentric)

                # location of the observer in HCC
                observer_hcc = observer_location.transform_to(frames.Heliocentric)

                # Distance from the observer to the body
                distance_observer_to_body = distance_between_locations_hcc(observer_hcc, body_hcc)

                # Distance of the body from the Sun
                distance_body_to_sun = np.sqrt(body_hcc.x**2 + body_hcc.y**2 + body_hcc.z**2)

                # Calculate the light travel time between the body and observer
                light_travel_time = (distance_observer_to_body / c).to(u.s)

                # The light from the planet reaches the observer at a time
                # later than the requested time.
                # The time index is unix time stamp in milliseconds - cast to
                # ints.
                time_that_photons_reach_observed = t #+ light_travel_time
                t_index = format_time_output(time_that_photons_reach_observed)

                # Create the data to be saved
                positions[observer_name][body_name][t_index] = dict()

                # Distance between the observer and the body
                positions[observer_name][body_name][t_index]["distance_observer_to_body_au"] = distance_format(distance_observer_to_body)

                # Distance between the body and the Sun.
                positions[observer_name][body_name][t_index]["distance_body_to_sun_au"] = distance_format(distance_body_to_sun)

                # Is the body behind the plane of the Sun?
                positions[observer_name][body_name][t_index]["behind_plane_of_sun"] = str(body_hcc.z.value < 0)

                # Store the positions of the body
                positions[observer_name][body_name][t_index]["x"] = position.Tx.value
                positions[observer_name][body_name][t_index]["y"] = position.Ty.value

            # Move the counter forward
            t += dt

        # Open the JSON file and dump out the positional information
        # if valid information was generated
        if save_file_for_this_duration:
            file_path = os.path.join(directory, file_name_format(observer_name, body_name, start_time))
            f = open(file_path, 'w')
            json.dump(positions, f)
            f.close()
