# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------ 
# Copyright (C) [2025] Instituto Nacional de Estadística 
# 
# Este archivo forma parte del proyecto INE MCP. 
# 
# Licenciado bajo la Licencia Pública de la Unión Europea (EUPL) v.1.2. 
# Puede obtener una copia de la licencia en la raiz de este proyecto o en: 
# https://eupl.eu/1.2/es/ 
# 
# A menos que se indique lo contrario, este software se distribuye 
# "TAL CUAL", SIN GARANTÍAS NI CONDICIONES DE NINGÚN TIPO. 
# Consulte la licencia para conocer los términos específicos. 
# ------------------------------------------------------------------------------ 
# Copyright (C) [2025] National Institute of Statistics 
# 
# This file is part of the INE MCP project. 
# 
# Licensed under the European Union Public License (EUPL) v.1.2. 
# You can obtain a copy of the license at the root of this project or at: 
# https://eupl.eu/1.2/es/ 
# 
# Unless otherwise indicated, this software is distributed 
# "AS IS", WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND. 
# See the license for specific terms. 
# ------------------------------------------------------------------------------ 

"""Pytest configuration: makes the package under src/ importable without installing it."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
