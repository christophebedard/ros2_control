# Copyright 2020 PAL Robotics S.L.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from controller_manager import list_controllers

from controller_manager_msgs.srv import \
    ConfigureStartController, LoadConfigureController, LoadStartController

import rclpy

from ros2cli.node.direct import DirectNode

from ros2node.api import NodeNameCompleter

from ros2param.api import call_list_parameters


def service_caller(service_name, service_type, request):
    try:
        rclpy.init()

        node = rclpy.create_node(
            'ros2controlcli_{}_requester'.format(
                service_name.replace(
                    '/', '')))

        cli = node.create_client(service_type, service_name)

        if not cli.service_is_ready():
            node.get_logger().debug('waiting for service {} to become available...'
                                    .format(service_name))
            if not cli.wait_for_service(2.0):
                raise RuntimeError('Could not contact service {}'.format(service_name))

        node.get_logger().debug('requester: making request: %r\n' % request)
        future = cli.call_async(request)
        rclpy.spin_until_future_complete(node, future)
        if future.result() is not None:
            return future.result()
        else:
            raise RuntimeError('Exception while calling service: %r' % future.exception())
    finally:
        node.destroy_node()
        rclpy.shutdown()


def load_configure_controller(controller_manager_name, controller_name):
    request = LoadConfigureController.Request()
    request.name = controller_name
    return service_caller('{}/load_and_configure_controller'.format(controller_manager_name),
                          LoadConfigureController, request)


def load_start_controller(controller_manager_name, controller_name):
    request = LoadStartController.Request()
    request.name = controller_name
    return service_caller('{}/load_and_start_controller'.format(controller_manager_name),
                          LoadStartController, request)


def configure_start_controller(controller_manager_name, controller_name):
    request = ConfigureStartController.Request()
    request.name = controller_name
    return service_caller('{}/configure_and_start_controller'.format(controller_manager_name),
                          ConfigureStartController, request)


class ControllerNameCompleter:
    """Callable returning a list of controllers parameter names."""

    def __call__(self, prefix, parsed_args, **kwargs):
        with DirectNode(parsed_args) as node:
            parameter_names = call_list_parameters(
                node=node, node_name=parsed_args.controller_manager)
            suffix = '.type'
            return [
                n[:-len(suffix)] for n in parameter_names
                if n.endswith(suffix)]


class LoadedControllerNameCompleter:
    """Callable returning a list of loaded controllers."""

    def __init__(self, valid_states=['active', 'inactive', 'configured', 'unconfigured']):
        self.valid_states = valid_states

    def __call__(self, prefix, parsed_args, **kwargs):
        with DirectNode(parsed_args) as node:
            controllers = list_controllers(node, parsed_args.controller_manager).controller
            return [
                c.name for c in controllers
                if c.state in self.valid_states]


def add_controller_mgr_parsers(parser):
    """Parser arguments to get controller manager node name, defaults to /controller_manager."""
    arg = parser.add_argument(
        '-c', '--controller-manager', help='Name of the controller manager ROS node',
        default='/controller_manager', required=False)
    arg.completer = NodeNameCompleter(
        include_hidden_nodes_key='include_hidden_nodes')
    parser.add_argument(
        '--include-hidden-nodes', action='store_true',
        help='Consider hidden nodes as well')
