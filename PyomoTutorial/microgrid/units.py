# -*- coding: utf-8 -*-
"""
Unit Class.

Basic block for modeling components.
"""

from pyomo.core.base.PyomoModel import Model as PyomoModel
from pyomo.core.base.block import SimpleBlock

import logging

__all__ = ['Unit']
logger = logging.getLogger('lms2.units')


class Unit(SimpleBlock):
    """
    redefinition of SimpleBlock
    """

    def __init__(self, *args, **kwds):
        """

        :param args:
        :param kwds:
        """
        super().__init__(*args, **kwds)
        logger.info(f'Initiation of {self.name}...')

    def __setattr__(self, key, value):

        super().__setattr__(key, value)
        logger.debug(f'adding the attribute : {key} = {value}')
