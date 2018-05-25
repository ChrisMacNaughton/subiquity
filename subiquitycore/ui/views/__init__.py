# Copyright 2015 Canonical, Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from .login import LoginView
from .network_bond_interfaces import NetworkBondInterfacesView
from .network_configure_interface import NetworkConfigureInterfaceView
from .network_configure_manual_interface import (
    NetworkConfigureIPv4InterfaceView, NetworkConfigureIPv6InterfaceView)
from .network_configure_wlan_interface import NetworkConfigureWLANView
from .network_default_route import NetworkSetDefaultRouteView
from .network import NetworkView
__all__ = [
    'LoginView',
    'NetworkBondInterfacesView',
    'NetworkConfigureInterfaceView',
    'NetworkConfigureIPv4InterfaceView',
    'NetworkConfigureIPv6InterfaceView',
    'NetworkConfigureWLANView',
    'NetworkSetDefaultRouteView',
    'NetworkView',
]
