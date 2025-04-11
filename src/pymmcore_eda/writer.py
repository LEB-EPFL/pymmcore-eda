from __future__ import annotations
from pymmcore_plus.mda.handlers import TensorStoreHandler
import useq

import shutil
import os
import json

import numpy as np

from smart_scan.custom_engine import CustomKeyes, GalvoParams

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Literal, TypeAlias
    TsDriver: TypeAlias = Literal["zarr", "zarr3", "n5", "neuroglancer_precomputed"]
    from os import PathLike
    from collections.abc import Mapping
    import tensorstore as ts
    import numpy as np
    from useq import FrameMetaV1

FRAME_DIM = "frame"

def serialize_custom_object(obj):
        """Convert custom objects to a JSON serializable format."""
        if isinstance(obj, CustomKeyes):
            return obj.value  # or some property of CustomKeyes that is serializable
        if isinstance(obj, GalvoParams):
            # Convert to a dictionary or list
            return obj.__dict__  # or choose specific attributes
        if isinstance(obj, np.ndarray):
            return obj.tolist()  # Convert numpy arrays to lists
        return obj  # If it's already serializable, return it as is

def save_metadata(metadata, tensorstore_path = r"C:\Users\tortarol\code\pymmcore-eda\test_data\20250411\\" ):
    # Define a path for the metadata JSON file
    metadata_path = tensorstore_path + "metadata.json"
    
    try:
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)
        print(f"Metadata saved to {metadata_path}")
    except Exception as e:
        print(f"[Metadata save error]: {e}")


class AdaptiveWriter(TensorStoreHandler):
    """A Tensorstorehandler that is optimized for adaptive acquisitions."""
    def __init__(
        self,
        *,
        n_channel : int,
        driver: TsDriver = "zarr",
        kvstore: str | dict | None = "memory://",
        path: str | PathLike | None = None,
        delete_existing: bool = False,
        spec: Mapping | None = None,
        
    ) -> None:
        super().__init__(driver=driver, kvstore=kvstore, path=path, delete_existing=delete_existing, spec=spec)
        # So we are flexible with what events are coming in
        self._nd_storage = False
        self.reshape_on_finished: bool = True
        self.n_channel = n_channel

    def sequenceFinished(self, seq: useq.MDASequence) -> None:
        super().sequenceFinished(seq)
        if not self._nd_storage and self.reshape_on_finished:
                self._reshape_store()
                shutil.rmtree(self._store.spec().kvstore.path, ignore_errors=True)
                self._store = self._res_store

    def new_store(
        self, frame: np.ndarray, seq: useq.MDASequence | None, meta: FrameMetaV1
    ) -> ts.Future[ts.TensorStore]:
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
    
    
    def frameReady(
            self, frame: np.ndarray, event: useq.MDAEvent, meta: FrameMetaV1
        ) -> None:
        if event.index.get("c", 0) == self.n_channel:
            
            # Save metadata into Zarr array attrs with unique key (e.g. mask)
            try:
                # Deep copy and serialize full metadata
                full_metadata = event.metadata.copy()

               #  Convert non-serializable objects (numpy arrays, custom objects) to serializable formats
                for k, v in full_metadata.items():
                    if isinstance(v, dict):  # If the value is a dictionary, process its items
                        for sub_k, sub_v in v.items():
                            v[sub_k] = serialize_custom_object(sub_v)
                    else:
                        full_metadata[k] = serialize_custom_object(v)

                # Get the path to the tensor store (assuming self._get_tensor_store() provides it)
                # tensor_store_path = self._get_tensor_store_path()  # Adjust this method as needed
                save_metadata(metadata = full_metadata)# , tensorstore_path=self.kvstore)
            except Exception as e:
                print(f"[Metadata save error]: {e}")
            
            
            # Old version
            # try:
            #     # convert metadata to json for writing, only if event is smart scan 
            #     new_metadata = event.metadata.copy()
            #     new_metadata['0'][0] = json.dumps({'0': event.metadata['0'][0].tolist()})
            #     event = event.replace(metadata = new_metadata)
            #     meta['mda_event'] = meta['mda_event'].replace(metadata = {})
            # except:
            #     pass

        super().frameReady(frame, event, meta)


    def get_shape_chunks_labels(self, frame_shape, seq):
        if not self._nd_storage:
            return (
                (self._size_increment, *frame_shape),
                (1, *frame_shape),
                (FRAME_DIM, "y", "x"),
            )
        return super().get_shape_chunks_labels(frame_shape, seq)

    def get_spec(self) -> dict:
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
            keys, values = zip(*dict(index).items())
            put_index = self._ts.d[keys][values]
            self._futures.append(self._res_store[put_index].write(self._store[pos]))
        while self._futures:
            self._futures.pop().result()

    def _get_reshape_spec(self) -> dict:
        spec = self.get_spec()
        spec["kvstore"] = spec["kvstore"].replace("_tmp", "")
        return spec