import os
import re
import tempfile
from datetime import datetime

import attr
import pyblish.api

import c4d

from ayon_cinema4d.api import plugin
from ayon_core.lib import get_version_from_path

from ayon_core.pipeline.create import get_product_name

# INSTANCE PLUGIN

class CollectRender(plugin.Cinema4DInstancePlugin):
    """Collect render instances for farm submission."""
    label = "Collect Render"
    order = pyblish.api.CollectorOrder
    hosts = ["cinema4d"]
    families = ["render"]  # Matches product_type from your Creator

    def process(self, instance):
        if instance.data["family"] == "workfile":
            return
            # instance.data["active"] = False
            # return

        if not instance.data.get("active", True):
            self.log.debug(f"Skipping inactive instance: {instance}")
            return

        render_target = instance.data.get("render_target", "farm")
        if render_target in ("farm", "farm_split"):
            instance.data["families"].append("render.farm")

        doc = c4d.documents.GetActiveDocument()
        if not doc:
            self.log.warning("No active document")
            return

        # collecting setting instance data
        product_name = get_product_name(project_name=instance.context.data["projectName"],
                                        task_name=instance.data.get("task"),
                                        task_type=instance.context.data.get("taskType") or instance.data.get(
                                            "taskType"), variant=instance.data.get("variant"),
                                        product_type=instance.data.get("productType"),
                                        host_name=instance.context.data.get("hostName") or instance.data.get("host"))
        self.log.debug(f"Collecting render for {product_name}")
        instance.data["productName"] = product_name

        instance.data["family"] = "render"
        instance.data["families"] = instance.data.get("families", []) + ["render"]

        instance.data["label"] = instance.data.get("variant", "Render")
        instance.data["name"] = instance.name

        fps = doc.GetFps()
        render_data = doc.GetActiveRenderData()
        frame_start = instance.data.get("frameStart")
        frame_end = instance.data.get("frameEnd")
        # instance.data["frameStart"] = frame_start
        # instance.data["frameEnd"] = frame_end
        instance.data["frameStart"] = render_data[c4d.RDATA_FRAMEFROM].GetFrame(fps)
        instance.data["frameEnd"] = render_data[c4d.RDATA_FRAMETO].GetFrame(fps)
        instance.data["frameStep"] = 1  # or doc.GetFrameStep() if relevant

        instance.data["resolutionWidth"] = doc[c4d.RDATA_XRES]
        instance.data["resolutionHeight"] = doc[c4d.RDATA_YRES]
        instance.data["pixelAspect"] = doc[c4d.RDATA_PIXELASPECT]

        instance.data["source"] = instance.context.data["currentFile"]
        self.log.debug(f"Source file: {instance.data['source']}")
        # instance.data["time"] = datetime.utcnow().isoformat()
        instance.data["version"] = 2024

        instance.data["review"] = instance.data.get("mark_for_review", True)

        # --- Extension ---
        extension_lookup = {
            c4d.FILTER_TIF: "tif",
            c4d.FILTER_PNG: "png",
            c4d.FILTER_JPG: "jpg",
            c4d.FILTER_EXR: "exr",
            c4d.FILTER_BMP: "bmp",
        }
        render_format = doc[c4d.RDATA_FORMAT]
        ext = extension_lookup.get(render_format, "png")
        self.log.debug(f"extension: {ext}")

        # --- Filename parts ---
        project_id = doc.GetDocumentName().split("_")[0]
        self.log.debug(f"Project name: {project_id}")
        folder = instance.context.data.get("folderPath", "nofolder").split("/")[-1]  # fallback
        self.log.debug(f"Folder: {folder}")
        product_name = instance.data["productName"]
        self.log.debug(f"Product name: {product_name}")
        version = int(get_version_from_path(instance.data["source"]))
        version += 1
        self.log.debug(f"Version: {version}")
        filepath = os.path.normpath(doc.GetDocumentPath() + "\\" + doc.GetDocumentName())
        instance.data["filePath"] = filepath
        instance.data["currentFile"] = os.path.normpath(doc.GetDocumentPath() + "\\" + doc.GetDocumentName())

        frame_start = instance.data["frameStart"]
        frame_end = instance.data["frameEnd"]

        # --- Output path ---
        # output_dir = os.path.normpath(tempfile.mkdtemp(prefix="c4d_render_", dir=os.path.dirname(instance.data["source"])) + "\\")
        base_dir = os.path.dirname(instance.data.get("source", tempfile.gettempdir()))
        output_dir = tempfile.mkdtemp(prefix="c4d_render_", dir=base_dir)
        output_dir = os.path.normpath(output_dir)

        instance.data["outputDir"] = output_dir
        self.log.debug(f"outputDir: {output_dir}")

        version -= 1

        # --- Expected file list ---
        expected = []
        for frame in range(frame_start, frame_end + 1):
            fname = f"{project_id}{folder}{product_name}{version}_{frame:04d}.{ext}"
            expected.append(os.path.normpath(os.path.join(output_dir, fname)))

        c4d_rd_path = os.path.normpath(os.path.join(output_dir, f"{project_id}{folder}{product_name}{version}.{ext}"))
        render_data[c4d.RDATA_PATH] = c4d_rd_path
        c4d.EventAdd()

        instance.data["expectedFiles"] = expected
        self.log.debug(f"Expected files: {expected}")

        rep = {
            "name": ext,
            "ext": ext,
            "files": [os.path.basename(f) for f in expected],
            "stagingDir": output_dir,
            "tags": ["review"] if instance.data.get("review") else [],
            "frameStart": instance.data["frameStart"],
            "frameEnd": instance.data["frameEnd"],
            "fps": fps
        }
        instance.data["representations"] = [rep]
        self.log.debug(f"Representation: {rep}")

        instance.data["farm"] = True

        version = int(str(c4d.GetC4DVersion())[:4])
        instance.data["hostVersion"] = version
        self.log.debug(f"Host version: {instance.data['hostVersion']}")

        instance.data["version"] = 2024
        instance.context.data["version"] = 2024
        self.log.debug(f"version: {instance.data['version']}")

        render_engine_id = render_data[c4d.RDATA_RENDERENGINE]
        RENDER_ENGINE_MAP = {
            0: "Standard",
            1: "Software",
            2: "Hardware",
            3: "Hardware 2.0",
            4: "External",
            5: "Physical",
            6: "Preview",
            1029988: "Redshift",
            1037639: "ProRender",
            1030488: "V-Ray",
            1053272: "Corona",
            1029525: "Octane",
        }
        render_engine_name = RENDER_ENGINE_MAP.get(render_engine_id, f"Unknown ({render_engine_id})")
        instance.data["renderEngine"] = render_engine_name
        self.log.debug(f"Render engine: {render_engine_name}")

    #
    #     render_data = doc.GetActiveRenderData()
    #     if not render_data:
    #         self.log.warning("No active render data")
    #         return
    #
    #     render_path = render_data[c4d.RDATA_PATH] or ""
    #     self.log.debug(f"Render path: {render_path}")
    #     render_format = render_data[c4d.RDATA_FORMAT]
    #     self.log.debug(f"Render format: {render_format}")
    #     render_name = os.path.splitext(doc.GetDocumentName())[0] + "_"
    #     self.log.debug(f"Render name: {render_name}")
    #     name_format = render_data[c4d.RDATA_NAMEFORMAT]
    #     self.log.debug(f"Render name format: {name_format}")
    #
    #     extension_lookup = {
    #         c4d.FILTER_TIF: "tif",
    #         c4d.FILTER_PNG: "png",
    #         c4d.FILTER_JPG: "jpg",
    #         c4d.FILTER_EXR: "exr",
    #         c4d.FILTER_BMP: "bmp",
    #     }
    #     ext = extension_lookup.get(render_format, "unk")
    #     self.log.debug(f"Render extension: {ext}")
    #
    #     name_formats = {
    #         0: "{name}####.{ext}",  # Name0001.tif
    #         1: "{name}####",        # Name0001
    #         2: "{name}.{ext}",      # Name.tif
    #         3: "{name}",            # Name
    #     }
    #     pattern = name_formats.get(name_format, "{name}####.{ext}")
    #     filename = pattern.format(name=render_name, ext=ext)
    #
    #     full_path = os.path.join(os.path.dirname(render_path), filename)
    #     instance.data["filePath"] = full_path
    #     self.log.debug(f"Resolved full render path: {full_path}")
    #
    #     render_engine_id = render_data[c4d.RDATA_RENDERENGINE]
    #     RENDER_ENGINE_MAP = {
    #         0: "Standard",
    #         1: "Software",
    #         2: "Hardware",
    #         3: "Hardware 2.0",
    #         4: "External",
    #         5: "Physical",
    #         6: "Preview",
    #         1029988: "Redshift",
    #         1037639: "ProRender",
    #         1030488: "V-Ray",
    #         1053272: "Corona",
    #         1029525: "Octane",
    #     }
    #     render_engine_name = RENDER_ENGINE_MAP.get(render_engine_id, f"Unknown ({render_engine_id})")
    #     instance.data["renderEngine"] = render_engine_name
    #     self.log.debug(f"Render engine: {render_engine_name}")
    #
    #     # Frame range
    #     fps = doc.GetFps()
    #     frame_start = render_data[c4d.RDATA_FRAMEFROM].GetFrame(fps)
    #     frame_end = render_data[c4d.RDATA_FRAMETO].GetFrame(fps)
    #     frame_step = int(render_data[c4d.RDATA_FRAMESTEP])
    #
    #     instance.data["frameStart"] = frame_start
    #     instance.data["frameEnd"] = frame_end
    #     instance.data["frameStep"] = frame_step
    #     instance.data["handleStart"] = 0
    #     instance.data["handleEnd"] = 0
    #     instance.data["step"] = 1
    #     instance.data["fps"] = fps
    #
    #     # Resolution
    #     instance.data["resolutionWidth"] = render_data[c4d.RDATA_XRES]
    #     instance.data["resolutionHeight"] = render_data[c4d.RDATA_YRES]
    #     instance.data["pixelAspect"] = render_data[c4d.RDATA_PIXELASPECT]
    #
    #     # Misc
    #     instance.data["review"] = bool(instance.data.get("review", False))
    #     instance.data["useSequenceForReview"] = instance.data.get("review", False)
    #     instance.data["attachTo"] = []
    #     instance.data["transfer"] = False
    #
    #     expected_files = [
    #         full_path.replace("####", f"{i:04d}")
    #         for i in range(instance.data["frameStart"], instance.data["frameEnd"] + 1)
    #     ]
    #     instance.data["expectedFiles"] = expected_files
    #     self.log.debug(f"Expected files: {expected_files}")
    #
    #     instance.data["representations"] = [{
    #         "name": ext,
    #         "ext": ext,
    #         "stagingDir": os.path.dirname(render_path),
    #         "files": expected_files,  # Important fix
    #         "tags": []
    #     }]
    #
    #     self.log.debug(f"Render name os.path.dirname: {os.path.dirname(render_path)}")
    #
    #     instance.data["farm"] = True
    #
    #     instance.data["currentFile"] = os.path.normpath(doc.GetDocumentPath() + "\\" + doc.GetDocumentName())
    #     self.log.info(f"Current file: {instance.data['currentFile']}")
    #     instance.data["host"]: pyblish.api.current_host()
    #
    #     version = int(str(c4d.GetC4DVersion())[:4])
    #     instance.data["hostVersion"] = version
    #     self.log.debug(f"Host version: {instance.data['hostVersion']}")
    #
    #     instance.data["outputDir"] = os.path.dirname(instance.data["currentFile"])
    #
    #     instance.data["version"] = 2024
    #     instance.context.data["version"] = get_version_from_path(render_name)
    #     self.log.debug(f"version: {instance.data['version']}")
    #
    #     rd = doc.GetActiveRenderData()
    #     render_name = str(os.path.normpath(doc.GetDocumentPath() + "\\" + os.path.splitext(doc.GetDocumentName())[0] + "_" + "." + ext))
    #     rd[c4d.RDATA_PATH] = render_name
    #     c4d.EventAdd()

# import os
# import re
# import tempfile
# from datetime import datetime
#
# import attr
# import pyblish.api
#
# import c4d
#
# from ayon_cinema4d.api import plugin
# from ayon_core.lib import get_version_from_path
#
#
# # INSTANCE PLUGIN
#
# class CollectRender(plugin.Cinema4DInstancePlugin):
#     """Collect render instances for farm submission."""
#     label = "Collect Render"
#     order = pyblish.api.CollectorOrder
#     hosts = ["cinema4d"]
#     families = ["render"]  # Matches product_type from your Creator
#
#     def _set_expected_files(self, instance):
#         """Build expectedFiles for render instances based on frame range and file naming pattern."""
#         file_path = instance.data.get("filePath")
#         if not file_path or "####" not in file_path:
#             self.log.warning(f"File path pattern missing or invalid: {file_path}")
#             return
#
#         frame_start = instance.data.get("frameStart")
#         frame_end = instance.data.get("frameEnd")
#         if frame_start is None or frame_end is None:
#             self.log.warning("Frame range is not defined.")
#             return
#
#         ext = instance.data.get("ext") or os.path.splitext(file_path)[1].lstrip(".")
#
#         expected_files = [
#             file_path.replace("####", f"{frame:04d}")
#             for frame in range(frame_start, frame_end + 1)
#         ]
#         instance.data["expectedFiles"] = expected_files
#
#         instance.data["representations"] = [{
#             "name": ext,
#             "ext": ext,
#             "stagingDir": os.path.dirname(file_path),
#             "files": [os.path.basename(f) for f in expected_files],
#             "tags": []
#         }]
#         self.log.debug(f"Built {len(expected_files)} expected files with pattern: {file_path}")
#
#     def process(self, instance):
#         if not instance.data.get("active", True):
#             self.log.debug(f"Skipping inactive instance: {instance}")
#             return
#
#         # instance.data["farm"] = True
#         # instance.context.data["increment_script_version"] = False
#
#         doc = c4d.documents.GetActiveDocument()
#         if not doc:
#             self.log.warning("No active document")
#             return
#
#         render_data = doc.GetActiveRenderData()
#         if not render_data:
#             self.log.warning("No active render data")
#             return
#
#         extension_lookup = {
#             c4d.FILTER_TIF: "tif",
#             c4d.FILTER_PNG: "png",
#             c4d.FILTER_JPG: "jpg",
#             c4d.FILTER_EXR: "exr",
#             c4d.FILTER_BMP: "bmp",
#         }
#
#         render_format = render_data[c4d.RDATA_FORMAT]
#         name_format = render_data[c4d.RDATA_NAMEFORMAT]
#         ext = extension_lookup.get(render_format, "unk")
#         product_name = instance.data.get("productName", "render")
#         doc_name = os.path.splitext(doc.GetDocumentName())[0]
#         version = get_version_from_path(doc_name)
#         render_name = f"{doc_name}_{product_name}v{version:03d}####.{ext}"
#         render_path = os.path.join(doc.GetDocumentPath(), render_name)
#         rd = doc.GetActiveRenderData()
#         rd[c4d.RDATA_PATH] = render_path
#
#         # render_path = render_data[c4d.RDATA_PATH] or ""
#         # self.log.debug(f"Render path: {render_path}")
#         #  self.log.debug(f"Render format: {render_format}")
#         # render_name = os.path.splitext(doc.GetDocumentName())[0] + "_"
#         # self.log.debug(f"Render name: {render_name}")
#
#         # self.log.debug(f"Render name format: {name_format}")
#
#         name_formats = {
#             0: "{name}####.{ext}",  # Name0001.tif
#             1: "{name}####",        # Name0001
#             2: "{name}.{ext}",      # Name.tif
#             3: "{name}",            # Name
#         }
#         pattern = name_formats.get(name_format, "{name}####.{ext}")
#         filename = pattern.format(name=render_name, ext=ext)
#
#         full_path = os.path.join(os.path.dirname(render_path), filename)
#         instance.data["filePath"] = full_path
#         self.log.debug(f"Resolved full render path: {full_path}")
#
#         render_engine_id = render_data[c4d.RDATA_RENDERENGINE]
#         RENDER_ENGINE_MAP = {
#             0: "Standard",
#             1: "Software",
#             2: "Hardware",
#             3: "Hardware 2.0",
#             4: "External",
#             5: "Physical",
#             6: "Preview",
#             1029988: "Redshift",
#             1037639: "ProRender",
#             1030488: "V-Ray",
#             1053272: "Corona",
#             1029525: "Octane",
#         }
#         render_engine_name = RENDER_ENGINE_MAP.get(render_engine_id, f"Unknown ({render_engine_id})")
#         instance.data["renderEngine"] = render_engine_name
#         self.log.debug(f"Render engine: {render_engine_name}")
#
#         # Frame range
#         fps = doc.GetFps()
#         # frame_start = render_data[c4d.RDATA_FRAMEFROM].GetFrame(fps)
#         # frame_end = render_data[c4d.RDATA_FRAMETO].GetFrame(fps)
#         frame_step = int(render_data[c4d.RDATA_FRAMESTEP])
#
#         # instance.data["frameStart"] = frame_start
#         # instance.data["frameEnd"] = frame_end
#         # instance.data["handleStart"] = 0
#         # instance.data["handleEnd"] = 0
#         instance.data["frameStep"] = frame_step
#         instance.data["step"] = 1
#         instance.data["fps"] = fps
#
#         # Resolution
#         instance.data["resolutionWidth"] = render_data[c4d.RDATA_XRES]
#         instance.data["resolutionHeight"] = render_data[c4d.RDATA_YRES]
#         instance.data["pixelAspect"] = render_data[c4d.RDATA_PIXELASPECT]
#
#         # Misc
#         instance.data["review"] = bool(instance.data.get("review", False))
#         instance.data["useSequenceForReview"] = instance.data.get("review", False)
#         instance.data["attachTo"] = []
#         instance.data["transfer"] = False
#
#         self._set_expected_files(instance)
#         # expected_files = [
#         #     full_path.replace("####", f"{i:04d}")
#         #     for i in range(instance.data["frameStart"], instance.data["frameEnd"] + 1)
#         # ]
#         # instance.data["expectedFiles"] = expected_files
#         # self.log.debug(f"Expected files: {expected_files}")
#         #
#         # instance.data["representations"] = [{
#         #     "name": ext,
#         #     "ext": ext,
#         #     "stagingDir": os.path.dirname(render_path),
#         #     "files": expected_files,  # Important fix
#         #     "tags": []
#         # }]
#
#         self.log.debug(f"Render name os.path.dirname: {os.path.dirname(render_path)}")
#
#         instance.data["currentFile"] = os.path.normpath(doc.GetDocumentPath() + "\\" + doc.GetDocumentName())
#         self.log.info(f"Current file: {instance.data['currentFile']}")
#         instance.data["host"]: pyblish.api.current_host()
#
#         version = int(str(c4d.GetC4DVersion())[:4])
#         instance.data["hostVersion"] = version
#         self.log.debug(f"Host version: {instance.data['hostVersion']}")
#
#         # instance.data["outputDir"] = os.path.dirname(instance.data["currentFile"])
#
#         instance.data["version"] = 2024
#         instance.context.data["version"] = get_version_from_path(render_name)
#         self.log.debug(f"version: {instance.data['version']}")
#
#         rd = doc.GetActiveRenderData()
#         render_name = str(os.path.normpath(doc.GetDocumentPath() + "\\" + os.path.splitext(doc.GetDocumentName())[0] + "_" + "." + ext))
#         rd[c4d.RDATA_PATH] = render_name
#         c4d.EventAdd()
