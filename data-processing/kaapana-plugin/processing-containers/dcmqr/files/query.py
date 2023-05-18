#!/usr/bin/env python3
#
# query.py: A small tool to query a DICOM PACS for new images using C-FIND
#
#
# References:
# - http://dicom.nema.org/Dicom/2013/output/chtml/part04/sect_C.4.html
# - http://dicom.nema.org/dicom/2013/output/chtml/part04/sect_C.3.html

import argparse
import logging
import jsonlines
import pydicom
import math

from typing import List
from pydicom.dataset import Dataset, DataElement
from pynetdicom import AE, debug_logger
from pynetdicom.status import code_to_status, code_to_category
from datetime import datetime, timedelta
from enum import Enum


log = logging.getLogger(__name__)


class QueryLevel(Enum):
    patient = "patient"
    study = "study"
    series = "series"
    instance = "instance"

    def __str__(self):
        return self.value


class DicomQueryClient:
    # This are the default tags used to form a C-Find query dataset (have a look at create_query_dataset)
    DEFAULT_TAGS = [
        "PatientName",
        "PatientID",
        "PatientBirthDate",
        "InstitutionName",
        "StudyInstanceUID",
        "StudyID",
        "StudyDate",
        "StudyTime",
        "StudyDescription",
        "PatientSex",
        "SeriesInstanceUID",
        "SeriesNumber",
        "StationName",
        "Modality",
        "Manufacturer",
        "ContrastBolusAgent",
        "AcquisitionDate",
    ]

    def __init__(self, aet: str, aec: str, peer: str, port: int, level: QueryLevel):
        self.log = logging.getLogger(__name__)
        self.log.setLevel(logging.DEBUG)
        self.ae = AE(ae_title=aet)

        # echo context
        # from pynetdicom.sop_class import VerificationSOPClass
        # self.ae.add_requested_context(VerificationSOPClass)
        self.level = level

        if level == QueryLevel.patient:
            from pynetdicom.sop_class import (
                PatientRootQueryRetrieveInformationModelFind,
            )

            self.query_model = PatientRootQueryRetrieveInformationModelFind
            self.level_string = "PATIENT"
        elif level == QueryLevel.study:
            from pynetdicom.sop_class import StudyRootQueryRetrieveInformationModelFind

            self.query_model = StudyRootQueryRetrieveInformationModelFind
            self.level_string = "STUDY"
        elif level == QueryLevel.series:
            # TODO: This works on chilli but not on dcm4chee
            from pynetdicom.sop_class import StudyRootQueryRetrieveInformationModelFind

            self.query_model = StudyRootQueryRetrieveInformationModelFind
            self.level_string = "SERIES"
        elif level == QueryLevel.instance:
            # TODO: implement me
            raise Exception(f"Query level {level} is currently not implemented")
        else:
            raise Exception(f"Query level {level} is currently not implemented")

        self.ae.add_requested_context(self.query_model)
        self.log.debug("Added %s context", self.query_model)
        self.log.info(
            "Initating association with %s:%s (Remote-AET: %s)", peer, port, aec
        )
        self.assoc = self.ae.associate(peer, port, ae_title=aec)
        if not self.assoc.is_established:
            raise Exception("Association is rejected aborted or never connected")

        self.log.info(
            "Successfull associated with %s:%s (Remote-AET: %s)", peer, port, aec
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.log.info("Releasing association")
        self.assoc.release()

    def date_range(self, ts1: datetime, ts2: datetime):
        return f"{'' if ts1 == None else ts1.strftime('%Y%m%d')}-{ '' if ts2 == None else ts2.strftime('%Y%m%d')}"

    def time_range(self, ts1: datetime, ts2: datetime):
        return f"{'' if ts1 == None else ts1.strftime('%H%M%S')}-{ '' if ts2 == None else ts2.strftime('%H%M%S')}"

    def create_query_dataset(self, tags: List = None) -> pydicom.dataset.Dataset:
        """Returnes a empty dicom dataset for using with C-Find. StudyDate is set when start_dt and end_dt are set.
        start_dt: datetime
        end_dt: datetime
        """

        ds = Dataset()

        # This would use all dicom tags from the dicom data directory unfortunatly this results in an error during c-find (pynetdcom problem?)
        # tags = pydicom.datadict.DicomDictionary.keys()
        if tags == None:
            self.log.debug("Used defautl tags")
            tags = self.DEFAULT_TAGS

        print(tags)

        for tag in tags:
            vr = pydicom.datadict.dictionary_VR(tag)
            ds.add(DataElement(tag, vr, None))

        ds.QueryRetrieveLevel = self.level_string

        return ds

    def set_time_frame(
        self,
        ds: pydicom.dataset.Dataset,
        start_dt: datetime = None,
        end_dt: datetime = None,
    ) -> pydicom.dataset.Dataset:
        if not start_dt and not end_dt:
            # No date to set
            return ds

        if self.level == QueryLevel.study or self.level == QueryLevel.series:
            # TODO: filter for ds.StudyTime
            ds.StudyDate = self.date_range(start_dt, end_dt)
            self.log.info("Query Date restictions StudyDate=%s", ds.StudyDate)
        if self.level == QueryLevel.patient:
            ds.InstanceCreationDate = self.date_range(start_dt, end_dt)
            self.log.info("Query Date restictions AcquisitionDate=%s", ds.StudyDate)

        return ds

    def execute_query(
        self,
        tags: List = None,
        limit: int = None,
        start_dt: datetime = None,
        end_dt: datetime = None,
    ):
        if self.level == QueryLevel.patient and limit:
            self.log.warn("Limited Querys are not supported")
            limit = None

        ds = self.create_query_dataset(tags)
        ds = self.set_time_frame(ds, start_dt, end_dt)

        if limit:
            return self.execute_limited_query(ds, limit, start_dt, end_dt)
        else:
            return self.execute_unlimited_query(ds)

    def execute_unlimited_query(self, ds: pydicom.dataset.Dataset):
        """Executes a DICOM C-FIND using the query dataset

        returns a generator"""
        self.log.info("Executing unlimited query")

        self.log.info("Sending C-Find on %s", self.query_model)
        responses = self.assoc.send_c_find(ds, self.query_model, priority=2)
        self.log.info("C-Find send, awaiting response...")

        received_cnt = 0
        error_cnt = 0
        for status, identifier in responses:
            received_cnt += 1
            if not status:
                error_cnt += 1
                self.log.error(
                    "Connection time out, abort or invalid response (Status: %s)",
                    code_to_category(status.Status),
                )
                # raise Exception("Connection time out, abort or invalid response")
            elif identifier is None and status.Status == 0:
                self.log.info("Retreived last item")
            elif identifier is None:
                self.log.error("None resultset")
            else:
                if self.level == QueryLevel.patient:
                    self.log.info(
                        "%d (errors: %d): status: %s PatientID: %s",
                        received_cnt,
                        error_cnt,
                        code_to_category(status.Status),
                        identifier.PatientID,
                    )
                else:
                    self.log.info(
                        "%d (errors: %d): status: %s StudyInstanceUID: %s",
                        received_cnt,
                        error_cnt,
                        code_to_category(status.Status),
                        identifier.StudyInstanceUID,
                    )
                yield identifier
        self.log.info(
            "Query Completed: Received %d, errors: %d", received_cnt, error_cnt
        )

    def execute_limited_query(
        self,
        ds: pydicom.dataset.Dataset,
        limit: int = 1000,
        start_dt: datetime = None,
        end_dt: datetime = None,
    ):
        """Tries to limit the results of a single query to stay under the given limit"""

        self.log.info("Executing limited query with limit %d", limit)

        def query_func(start, end):
            query = self.set_time_frame(ds, start, end)
            return self.execute_unlimited_query(query)

        if not end_dt:
            end_dt = datetime.now()

        return self._query_size_limiter(
            query_func=query_func, limit=limit, start_date=start_dt, end_date=end_dt
        )

    def _query_size_limiter(
        self,
        query_func,
        limit: int = 100,
        start_date: datetime = None,
        end_date: datetime = datetime.today(),
        MAX_ATTEMPTS: int = 10,
        WINDOW_INCREMENT_FACTOR: int = 2,
    ):
        assert MAX_ATTEMPTS > 0, "MAX_ATTEMPTS must be a positiv number"
        assert WINDOW_INCREMENT_FACTOR >= 1, "WINDOW_INCREMENT_FACTOR must be >= 1"
        assert limit > 0, "Query limit must be bigger than 0"
        assert start_date == None or start_date < end_date, "Start must be before end"

        # Initalization
        new_end_date = end_date
        # data per day - dpd is set to limit so that at first only one day is retreived
        # TODO: this is oftentimes a two short window, query a week maybe would be better or make it adjustable
        dpd = limit
        attempts_without_data = 0

        # Loop Terminates when query returns no data anymore or when the start date is reached
        while True:
            # Step 1 - Calculate new start date
            window_size = math.ceil(1 / dpd * limit)
            new_start_date = new_end_date - timedelta(days=window_size)
            self.log.debug(
                f"Preparing Query end date: %s, new start date: %s, dpd: %d, window_size %d",
                new_end_date,
                new_start_date,
                dpd,
                window_size,
            )

            if start_date != None and new_start_date <= start_date:
                new_start_date = start_date

            if math.ceil((new_end_date - new_start_date).days) == 0:
                self.log.info("Reached start_date")
                return

            if new_start_date >= new_end_date:
                assert False

            # Step 2 - Query New Data
            new_results = list(query_func(new_start_date, new_end_date))
            self.log.debug(f"Query returned %d results", len(new_results))
            new_dpd = len(new_results) / math.ceil((new_end_date - new_start_date).days)

            for r in new_results:
                yield r

            # Step 3 - Adjust query parameters for next round
            if new_dpd == 0:
                self.log.info(
                    "No data returned between %s and %s", new_start_date, new_end_date
                )
                attempts_without_data += 1
                new_dpd = dpd / WINDOW_INCREMENT_FACTOR
                self.log.info(
                    "Increasing window (attempt %d/%d) by factor %d (dpd is now: %f, was %f)",
                    attempts_without_data,
                    MAX_ATTEMPTS,
                    WINDOW_INCREMENT_FACTOR,
                    new_dpd,
                    dpd,
                )
                if attempts_without_data >= MAX_ATTEMPTS:
                    self.log.info(
                        "Last %d querys returned no result, aborting...",
                        attempts_without_data,
                    )
                    return
            else:
                attempts_without_data = 0

            new_end_date = new_start_date
            dpd = new_dpd


if __name__ == "__main__":
    logging.basicConfig()
    log.setLevel(logging.INFO)
    parser = argparse.ArgumentParser(
        description="""
Helper script to query PACS using C-FIND

note: tries to mimic dcmtk tools options
"""
    )
    parser.add_argument("peer", help="hostname of DICOM peer")
    parser.add_argument("port", type=int, help="tcp/ip port number of DICOM peer")
    parser.add_argument(
        "-aet",
        help="application entity title of the SCU (e.g. this script)",
        default="STORESCP",
    )
    parser.add_argument(
        "-aec",
        help="application entity title of the SCP (e.g. the peer)",
        default="ANY-SCP",
    )
    parser.add_argument(
        "--max-query-size",
        type=int,
        help="If set to a positiv value larger than 0, the query is chunked int smaller queries. The estimated size of a single query would be smaller or equal to this paremter",
        default=None,
    )
    parser.add_argument(
        "outfile", help="a jsonlines file containing the the resultset of this query"
    )
    parser.add_argument("-v", help="more verbose output", action="store_true")
    parser.add_argument(
        "--filter-uid",
        help="remove results without uid according to level",
        action="store_true",
    )
    parser.add_argument(
        "--start-date", help="An ISO 8601 datetime string (eg. 2021-03-11)"
    )
    parser.add_argument(
        "--end-date", help="An ISO 8601 datetime string (eg. 2021-03-11)"
    )
    parser.add_argument(
        "--level",
        help="What type of objects should be retreived",
        type=QueryLevel,
        choices=list(QueryLevel),
        default=QueryLevel.study,
    )
    args = parser.parse_args()

    if args.v:
        logging.basicConfig(level=logging.DEBUG)
        debug_logger()

    start_dt = datetime.fromisoformat(args.start_date) if args.start_date else None
    end_dt = datetime.fromisoformat(args.end_date) if args.end_date else None

    with DicomQueryClient(
        args.aet, args.aec, args.peer, args.port, args.level
    ) as client:
        path = args.outfile
        log.info("Opening result file %s", path)
        with jsonlines.open(path, mode="w") as writer:
            if args.max_query_size:
                logging.info("Max query size: %d", args.max_query_size)
                resultset = client.execute_query(
                    start_dt=start_dt, end_dt=end_dt, limit=args.max_query_size
                )
            else:
                resultset = client.execute_query(start_dt=start_dt, end_dt=end_dt)

            for result in resultset:
                if args.filter_uid:
                    filtered = False
                    if args.level == QueryLevel.patient and "PatientID" not in result:
                        filtered = True
                    elif (
                        args.level == QueryLevel.study
                        and "StudyInstanceUID" not in result
                    ):
                        filtered = True
                    elif (
                        args.level == QueryLevel.series
                        and "SeriesInstanceUID" not in result
                    ):
                        filtered = True

                    if filtered:
                        log.warn(
                            "Skipping Object because it does not contain correct identifier for level %s (Object: %s)",
                            args.level,
                            result,
                        )
                        continue

                writer.write(result.to_json_dict())

    log.info("All done")
