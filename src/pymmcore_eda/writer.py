from __future__ import annotations

import os
import shutil
from typing import TYPE_CHECKING

from pymmcore_plus.mda.handlers import TensorStoreHandler

if TYPE_CHECKING:
    from typing import Literal, TypeAlias

    import useq
    from useq import MDASequence

    TsDriver: TypeAlias = Literal["zarr", "zarr3", "n5", "neuroglancer_precomputed"]
    from collections.abc import Mapping
    from os import PathLike

    import numpy as np
    import tensorstore as ts
    from useq import FrameMetaV1

FRAME_DIM = "frame"


class AdaptiveWriter(TensorStoreHandler):
    """A Tensorstorehandler that is optimized for adaptive acquisitions."""

    def __init__(
        self,
        *,
        driver: TsDriver = "zarr",
        kvstore: str | dict | None = "memory://",
        path: str | PathLike | None = None,
        delete_existing: bool = False,
        spec: Mapping | None = None,
    ) -> None:
        super().__init__(
            driver=driver,
            kvstore=kvstore,
            path=path,
            delete_existing=delete_existing,
            spec=spec,
        )
        # So we are flexible with what events are coming in
        self._nd_storage = False
        self.reshape_on_finished: bool = True

    def sequenceFinished(self, seq: useq.MDASequence) -> None:
        """Clean up additionally, if self.reshape_on_finished is set."""
        super().sequenceFinished(seq)
        if not self._nd_storage and self.reshape_on_finished:
            self._reshape_store()
            shutil.rmtree(self._store.spec().kvstore.path, ignore_errors=True)  # type: ignore
            self._store = self._res_store

    def new_store(
        self, frame: np.ndarray, seq: useq.MDASequence | None, meta: FrameMetaV1
    ) -> ts.Future[ts.TensorStore]:
        """Create a new store for the sequence and given the frame shape."""
        shape, chunks, labels = self.get_shape_chunks_labels(frame.shape, seq)
        # self._nd_storage = FRAME_DIM not in labels
        return self._ts.open(
            self.get_spec(),
            create=True,
            delete_existing=self.delete_existing,
            dtype=self._ts.dtype(frame.dtype),
            shape=shape,
            chunk_layout=self._ts.ChunkLayout(chunk_shape=chunks),
            domain=self._ts.IndexDomain(labels=labels),
        )

    def get_shape_chunks_labels(
        self, frame_shape: tuple[int, ...], seq: MDASequence | None = None
    ) -> tuple:
        """Get the shape, chunks, and labels for the store."""
        if not self._nd_storage:
            return (
                (self._size_increment, *frame_shape),
                (1, *frame_shape),
                (FRAME_DIM, "y", "x"),
            )
        return super().get_shape_chunks_labels(frame_shape, seq)

    def get_spec(self) -> dict:
        """Get the spec for the store."""
        if self.reshape_on_finished and isinstance(self.kvstore, str):
            directory, filename = os.path.split(self.kvstore)
            base, *ext = filename.split(".")
            self.kvstore = os.path.join(
                directory, "".join([f"{base}_tmp"] + [f".{e}" for e in ext])
            )
        elif self.reshape_on_finished and not isinstance(self.kvstore, str):
            raise NotImplementedError("kvstore needs to be str for reshape to work")
        return super().get_spec()

    def _reshape_store(self) -> None:
        if self._store is None:
            return
        labels = [*list(self._axis_max.keys()), "y", "x"]
        chunks = [1] * (len(labels) - 2) + list(self._store.shape[-2:])
        shape = [x + 1 for x in self._axis_max.values()] + list(self._store.shape[-2:])
        self._res_store = self._ts.open(
            self._get_reshape_spec(),
            create=True,
            delete_existing=True,
            dtype=self._ts.dtype(self._store.dtype),
            shape=shape,
            chunk_layout=self._ts.ChunkLayout(chunk_shape=chunks),
            domain=self._ts.IndexDomain(labels=labels),
        ).result()
        for index, pos in self._frame_indices.items():
            keys, values = zip(*dict(index).items(), strict=False)
            put_index = self._ts.d[keys][values]
            self._futures.append(self._res_store[put_index].write(self._store[pos]))
        # Transfer metadata
        if source := self._store.kvstore:
            zattrs_bytes = source.read(".zattrs").result().value
            dest = self._res_store.kvstore
            self._futures.append(dest.write(".zattrs", zattrs_bytes))

        while self._futures:
            self._futures.pop().result()



    def _get_reshape_spec(self) -> dict:
        spec = self.get_spec()
        spec["kvstore"] = spec["kvstore"].replace("_tmp", "")
        return spec
