
from pyluno.api import Luno, LunoAPIRateLimitError

from . import utils

import os
import json
import pandas as pd
import time
import logging

logger = logging.getLogger(__name__)

# Set pyluno to warning only
logging.getLogger("pyluno").setLevel(logging.WARNING)

"""
Notes:
    - Everything is in seconds since EPOCH unless the api or something needs it
    converted
"""


class Collector(utils.BaseCollector):
    """TODO """
    def __init__(self, dataFile=None, dataDir=None, api=None):
        super(Collector, self).__init__(dataDir)
        self.logger = logging.getLogger(__name__)
        if dataFile is not None:
            self.dataFile = dataFile
        else:
            self.dataFile = 'luno_' + self.dataFile
        self.dataPath = os.path.join(self.dataDir, self.dataFile)
        if api is None:
            if os.path.isfile(os.path.join(self.rootDir, self.authFile)):
                with open(os.path.join(self.rootDir, self.authFile)) \
                 as authFile:
                    authJson = json.load(authFile)
                options = {'maxRate': 0.2, 'maxBurst': 5}
                self.api = Luno(authJson['key'], authJson['secret'], options)
                self.logger.info('Found auth file, created authenticated API')
            else:
                options = {'maxRate': 0.2, 'maxBurst': 5}
                self.api = Luno('', '', options)
                self.logger.warning('API not provided and no auth found.' +
                                    'Using non-authenticated (Reduced Rates)')
        else:
            self.api = api
        self._stop_time()

    def new_collection(self, fromtime):
        self._check_new_collection()
        df = self._get_data(fromtime)
        self._save_dataframe(df)
        self.logger.info('Complete. New collection fetched.')

    def collect(self):
        with pd.HDFStore(os.path.join(self.dataDir, self.dataFile)) as store:
            nrows = store.get_storer('trades').nrows
            lastval = store.select('trades', start=nrows - 1, stop=nrows)
            fromtime = ((lastval.index.astype(int).max())/10e8)
            self.logger.info('Last fetched time is: {}'.format(
                time.strftime('%Y-%m-%d %H:%M:%S',
                              time.localtime(fromtime))))
        df = self._get_data(fromtime)

        self._save_dataframe(df)
        self.logger.info('Complete. {} new trades added.'.format(len(df)))

    def _get_data(self, fromtime, df=pd.DataFrame()):
        fetchedtime = fromtime
        while fetchedtime < int(self.stoptime):
            try:
                dft = self.api.get_trades_frame(
                    since=int(round(fetchedtime*1000)))
            except LunoAPIRateLimitError as e:
                dft = pd.DataFrame()
                self.logger.error(e)
            if dft.empty:
                break
            fetchedtime = ((dft.index.astype(int).max())/10e8)
            df = pd.concat([df, dft])
            df = self._partial_save(df)
            self.logger.info('Getting data... Last call got to: {}'.format(
                time.strftime('%Y-%m-%d %H:%M:%S',
                              time.localtime(fetchedtime))))
        return df

    def _last_fetched(self):
        pass

    def _data_check(self):
        if os.path.isfile(os.path.join(self.dataDir, self.dataFile)):
            return 2
        elif os.path.isdir(self.dataDir):
            return 1
        else:
            return 0


class LunoSaver(utils.BaseClass):
    """TODO """
    def __init__(self):
        super(LunoSaver, self).__init__()
