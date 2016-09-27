# -*- coding: utf-8 -*-
"""
/***************************************************************************
 VectorCompare
                                 A QGIS plugin
 Comparaison of polygon layer - first for classifcation purposes
                             -------------------
        begin                : 2016-09-27
        copyright            : (C) 2016 by EOInt
        email                : gillian.milani@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load VectorCompare class from file VectorCompare.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .vector_compare import VectorCompare
    return VectorCompare(iface)
