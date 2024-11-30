"""Gets session data from HamStudy

Copyright (C) 2024  Jacob Humble

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import requests
import config

def get_sessions(
    zipcode: str = None,
    geo_long: str = None,
    geo_lat: str = None,
    max_distance: str = None,
    vec: str = None,
    team_id: str = None,
    start_date: str = None,
    end_date: str = None,
    exam_type: str = None,
    max_fee: str = None,
    include_full: bool = False) -> dict:
    """Gets session data from HamStudy that matches parameters

    Args:
        zipcode (str, optional): ZIP code to find exams near. Defaults to None.
        geo_long (str, optional): Longitude to find exams near. Defaults to None.
        geo_lat (str, optional): Latitude to find exams to. Defaults to None.
        max_distance (str, optional): How far should we look from origin for exams. Defaults to None.
        vec (str, optional): VEC to filter by, lowercase. Defaults to None.
        team_id (str, optional): team ID. Defaults to None.
        start_date (str, optional): earliest exam to show. Defaults to None.
        end_date (str, optional): latest exam to show. Defaults to None.
        exam_type (str, optional): remote, inperson, or all. Defaults to None.
        max_fee (str, optional): maximum fee to display. Defaults to None.
        include_full (bool, optional): include exams that are full. Defaults to False.

    Raises:
        response.raise_for_status: HTTPError

    Returns:
        dict of json elements in response
    """

    with requests.Session() as session:
        session.params = {
            k: v
            for k, v in {
                "zip": zipcode,
                "geo.long": geo_long,
                "geo.lat": geo_lat,
                "maxDistance": max_distance,
                "vec": vec,
                "team": team_id,
                "startDate": start_date,
                "endDate": end_date,
                "type": exam_type,
                "maxFee": max_fee,
                "includeFull": include_full,
            }.items()
            if v is not None
        }

        session.headers = {
            'User-Agent': config.USER_AGENT
        }
    response = session.get("https://hamstudy.org/api/v1/sessions", timeout=5)
    if response.status_code is not requests.codes.ok:
        raise response.raise_for_status

    return response.json()
