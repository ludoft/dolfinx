# Copyright (C) 2013 Anders Logg
#
# This file is part of DOLFINX (https://www.fenicsproject.org)
#
# SPDX-License-Identifier:    LGPL-3.0-or-later

import mpi4py
import numpy
import pytest
from mpi4py import MPI

from dolfinx import Mesh, UnitCubeMesh, UnitIntervalMesh, UnitSquareMesh, cpp
from dolfinx.cpp.mesh import CellType
from dolfinx_utils.test.skips import skip_in_parallel


@skip_in_parallel
def test_distance_interval():
    mesh = UnitIntervalMesh(MPI.COMM_SELF, 1)
    assert cpp.geometry.squared_distance(mesh, mesh.topology.dim, 0, numpy.array([-1.0, 0, 0])) == pytest.approx(1.0)
    assert cpp.geometry.squared_distance(mesh, mesh.topology.dim, 0, numpy.array([0.5, 0, 0])) == pytest.approx(0.0)


@skip_in_parallel
def test_distance_triangle():
    mesh = UnitSquareMesh(MPI.COMM_SELF, 1, 1)
    assert cpp.geometry.squared_distance(mesh, mesh.topology.dim, 1,
                                         numpy.array([-1.0, -1.0, 0.0])) == pytest.approx(2.0)
    assert cpp.geometry.squared_distance(mesh, mesh.topology.dim, 1,
                                         numpy.array([-1.0, 0.5, 0.0])) == pytest.approx(1.0)
    assert cpp.geometry.squared_distance(mesh, mesh.topology.dim, 1, numpy.array([0.5, 0.5, 0.0])) == pytest.approx(0.0)


@skip_in_parallel
def test_distance_tetrahedron():
    mesh = UnitCubeMesh(MPI.COMM_SELF, 1, 1, 1)
    assert cpp.geometry.squared_distance(mesh, mesh.topology.dim, 5,
                                         numpy.array([-1.0, -1.0, -1.0])) == pytest.approx(3.0)
    assert cpp.geometry.squared_distance(mesh, mesh.topology.dim, 5,
                                         numpy.array([-1.0, 0.5, 0.5])) == pytest.approx(1.0)
    assert cpp.geometry.squared_distance(mesh, mesh.topology.dim, 5, numpy.array([0.5, 0.5, 0.5])) == pytest.approx(0.0)


@pytest.mark.parametrize(
    'mesh', [
        UnitIntervalMesh(MPI.COMM_WORLD, 8),
        UnitSquareMesh(MPI.COMM_WORLD, 8, 9, CellType.triangle),
        UnitSquareMesh(MPI.COMM_WORLD, 8, 9, CellType.quadrilateral),
        UnitCubeMesh(MPI.COMM_WORLD, 8, 9, 5, CellType.tetrahedron)
    ])
def test_volume_cells(mesh):
    tdim = mesh.topology.dim
    map = mesh.topology.index_map(tdim)
    num_cells = map.size_local
    v = cpp.mesh.volume_entities(mesh, range(num_cells), mesh.topology.dim)
    assert mesh.mpi_comm().allreduce(v.sum(), mpi4py.MPI.SUM) == pytest.approx(1.0, rel=1e-9)


def test_volume_quadrilateralR2():
    mesh = UnitSquareMesh(MPI.COMM_SELF, 1, 1, CellType.quadrilateral)
    assert cpp.mesh.volume_entities(mesh, [0], mesh.topology.dim) == 1.0


@pytest.mark.parametrize(
    'coordinates',
    [[[0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0]],
     [[0.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [0.0, 1.0, 1.0]]])
def test_volume_quadrilateralR3(coordinates):
    mesh = Mesh(MPI.COMM_SELF, CellType.quadrilateral,
                numpy.array(coordinates, dtype=numpy.float64),
                numpy.array([[0, 1, 2, 3]], dtype=numpy.int32), [])
    mesh.topology.create_connectivity_all()
    assert cpp.mesh.volume_entities(mesh, [0], mesh.topology.dim) == 1.0


@pytest.mark.parametrize(
    'scaling',
    [1e0, 1e-5, 1e-10, 1e-15, 1e-20, 1e-30, 1e5, 1e10, 1e15, 1e20, 1e30])
def test_volume_quadrilateral_coplanarity_check_1(scaling):
    with pytest.raises(RuntimeError) as error:
        # Unit square cell scaled down by 'scaling' and the first vertex
        # is distorted so that the vertices are clearly non coplanar
        mesh = Mesh(MPI.COMM_SELF, CellType.quadrilateral,
                    numpy.array([[scaling, 0.5 * scaling, 0.6 * scaling], [0.0, scaling, 0.0],
                                 [0.0, 0.0, scaling], [0.0, scaling, scaling]], dtype=numpy.float64),
                    numpy.array([[0, 1, 2, 3]],
                                dtype=numpy.int32), [])

        mesh.topology.create_connectivity_all()
        cpp.mesh.volume_entities(mesh, [0], mesh.topology.dim)

    assert "Not coplanar" in str(error.value)


# Test when |p0-p3| is ~ 1 but |p1-p2| is small
# The cell is degenerate when scale is below 1e-17, it is expected to fail the test.
@pytest.mark.parametrize('scaling', [1e0, 1e-5, 1e-10, 1e-15])
def test_volume_quadrilateral_coplanarity_check_2(scaling):
    with pytest.raises(RuntimeError) as error:
        # Unit square cell scaled down by 'scaling' and the first vertex
        # is distorted so that the vertices are clearly non coplanar
        mesh = Mesh(MPI.COMM_SELF, CellType.quadrilateral,
                    numpy.array(
                        [[1.0, 0.5, 0.6], [0.0, scaling, 0.0],
                         [0.0, 0.0, scaling], [0.0, 1.0, 1.0]],
                        dtype=numpy.float64),
                    numpy.array([[0, 1, 2, 3]], dtype=numpy.int32), [])
        mesh.topology.create_connectivity_all()
        cpp.mesh.volume_entities(mesh, [0], mesh.topology.dim)

    assert "Not coplanar" in str(error.value)
