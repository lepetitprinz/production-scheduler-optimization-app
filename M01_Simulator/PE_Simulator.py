# -*- coding: utf-8 -*-

import datetime

from M03_Site import simFactoryMgr
from M02_DataManager import dbDataMgr
from M03_Site import simFactoryMgr, simOperMgr
from M04_PhyProductionMgr import objWarehouse
from M05_ProductManager import objLot
from M06_Utility import comUtility

import numpy as np
from itertools import permutations

class Simulator:
    def __init__(self):
        self._util = comUtility.Utility
        self.DataMgr: dbDataMgr.DataManager = None
        self._whNgr: objWarehouse.Warehouse = None
        self._facObjList: list = []

    def SetupDbObject(self, source: str, day_start_time: str, dmdMonth: int = None):
        self.DataMgr = dbDataMgr.DataManager(source=source, dmdMonth=dmdMonth)
        engConfData = self.DataMgr.SetupEngConfData()
        self._util.setupObject(simul=self, engConfig=engConfData)

        year = int(self._util.PlanStartTime[:4])
        month = int(self._util.PlanStartTime[4:6])
        day = int(self._util.PlanStartTime[6:])

        schedStartTime = self._util.PlanStartTime
        schedEndTime = self._util.PlanEndTime
        schedStartDateTime = datetime.datetime.strptime(schedStartTime, '%Y%m%d')
        schedEndDateTime = datetime.datetime.strptime(schedEndTime, '%Y%m%d')
        schedPeriod = str(schedEndDateTime - schedStartDateTime)
        schedPeriodDays = int(schedPeriod.split()[0]) + 1
        horizon_days = schedPeriodDays  # 고정값 처리 가능

        siloCapa = self._util.SiloCapa
        SiloQty = self._util.SiloQty

        # Bagging Lead Time 제약
        if self._util.BaggingLeadTimeConst == True:
            silo_wait_hours = self._util.BaggingLeadTime
        else:
            silo_wait_hours = 0

        # DB에 있는 Data 정보 받아오는 처리
        self.DataMgr.SetupObject()
        self.DataMgr.build_demand_max_days_by_month()
        engConfig = self.DataMgr.dbEngConf
        #self._util.setupObject(simul=self, engConfig=engConfig)
        # self._util.set_runtime(runtime=0)

        print("=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*= Configuration Information =*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=")
        print("=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=")

        # Factory 인스턴스 세팅
        if self.DataMgr.dmdMonth is not None:
            self._create_new_factory(factory_id="GS_CALTEX", day_start_time=day_start_time,
                                     year=comUtility.Utility.DayStartDate.year,
                                     month=comUtility.Utility.DayStartDate.month,
                                     day=comUtility.Utility.DayStartDate.day,
                                     horizon_days=comUtility.Utility.DayHorizon.days,
                                     silo_qty=comUtility.Utility.SiloCapa,
                                     nof_silo=SiloQty, silo_wait_hours=int(silo_wait_hours))
        else:
            self._create_new_factory(factory_id="GS_CALTEX", day_start_time=day_start_time, year=year, month=month,
                                     day=day,
                                     horizon_days=comUtility.Utility.DayHorizon.days,
                                     silo_qty=comUtility.Utility.SiloCapa,
                                     nof_silo=SiloQty, silo_wait_hours=silo_wait_hours)
        flag = self.SetupObject()

    def SetupObject(self):

        operObj: simOperMgr = None
        facID: str = ""

        for obj in self._facObjList:
            facObj: simFactoryMgr = obj
            facObj.SetupResumeData()    # 현재 RM warehouse만 setting
            facObj.sendInitEvent()      # 공장 객체 초기화 정보를 DB에 전달(미구현)

    def run_simulator(self):
        if len(self._facObjList) < 1:
            # Factory가 없는 경우?
            print("Factory 객체 없음")
            raise AssertionError()
        elif len(self._facObjList) == 1:
            self._run_single_factory()
        else:
            self._run_multi_factory()

    def _run_single_factory(self):
        facObj: simFactoryMgr.Factory = self._facObjList[0]
        # 머신 깨우기
        facObj.wake_up_machine()
        # Lot 할당
        # facObj.AssignLot()

        # Factory 초기 시작시간 셋팅
        self._util.set_runtime(runtime=self._util.DayStartDate)

        # Factory 가동 시작
        facObj.run_factory()

    def _run_multi_factory(self):
        pass

    def _create_new_factory(self, factory_id: str, day_start_time: str, year: int, month: int, day: int, horizon_days: int, silo_qty: int, nof_silo: int, silo_wait_hours: int = 0):
        facObj: simFactoryMgr = simFactoryMgr.Factory(simul=self, facID=factory_id)
        facObj.SetupObject(
            dayStartTime=day_start_time,
            year=year,
            month=month,
            day=day,
            horizon_days=horizon_days,
            silo_qty=silo_qty,
            nof_silo=nof_silo,
            silo_wait_hours=silo_wait_hours
        )
        self._facObjList.append(facObj)

    def SaveSimulData(self):
        # self.DataMgr.SaveEngConfig()
        prodScheduleRslt = []

        if len(self._facObjList) == 1:
            facObj: simFactoryMgr.Factory = self._facObjList[0]
            for wh in facObj.WhouseObjList:
                whObj:objWarehouse.Warehouse = wh
                if whObj.Kind == 'FGI':
                    prodScheduleRslt = whObj.ProdScheduleRsltArr

            self.DataMgr.SaveProdScheduleRslt(prodScheduleRslt=prodScheduleRslt)
