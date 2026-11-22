"""Start Java, a single-node HDFS and a Spark session on Kaggle (also works on Colab/Linux).

Usage in a notebook:
    from t15 import env
    spark = env.start(cores=4)          # HDFS + Spark
    spark = env.start(hdfs=False)       # Spark on local disk only
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

HADOOP_VERSION = "3.3.6"
HADOOP_URLS = [
    f"https://archive.apache.org/dist/hadoop/common/hadoop-{HADOOP_VERSION}/hadoop-{HADOOP_VERSION}.tar.gz",
    f"https://dlcdn.apache.org/hadoop/common/hadoop-{HADOOP_VERSION}/hadoop-{HADOOP_VERSION}.tar.gz",
]
SPARK_PIP = "pyspark==4.0.1"   # Kaggle runs Python 3.13: needs Spark 4
HADOOP_HOME = Path("/opt/hadoop")
HDFS_DATA = Path("/tmp/hdfs-data")


def sh(cmd: str, check: bool = True, quiet: bool = False) -> str:
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if not quiet and r.stdout.strip():
        print(r.stdout.strip()[-2000:])
    if check and r.returncode != 0:
        raise RuntimeError(f"Command failed ({r.returncode}): {cmd}\n{r.stderr[-3000:]}")
    return r.stdout


def _java_home() -> str | None:
    for cand in [os.environ.get("JAVA_HOME"), "/usr/lib/jvm/java-17-openjdk-amd64",
                 "/usr/lib/jvm/java-11-openjdk-amd64", "/usr/lib/jvm/default-java"]:
        if cand and Path(cand, "bin", "java").exists():
            return cand
    java = shutil.which("java")
    if java:
        return str(Path(os.path.realpath(java)).parents[1])
    return None


def install_java() -> str:
    jh = _java_home()
    if jh is None:
        print("Installing OpenJDK 17 ...")
        sh("apt-get -qq update && apt-get -qq install -y openjdk-17-jdk-headless > /dev/null", quiet=True)
        jh = _java_home()
    if jh is None:
        raise RuntimeError("Java not found after install. Enable Internet in the Kaggle notebook settings.")
    os.environ["JAVA_HOME"] = jh
    return jh


def install_spark():
    try:
        import pyspark  # noqa: F401
        if int(pyspark.__version__.split(".")[0]) < 4:
            raise ImportError
    except ImportError:
        print(f"Installing {SPARK_PIP} ...")
        sh(f"{sys.executable} -m pip install -q {SPARK_PIP}", quiet=True)


def install_hadoop(tarball_dirs: list[Path] | None = None):
    """Install Hadoop. Uses a tarball from an attached Kaggle Dataset if present (faster)."""
    if (HADOOP_HOME / "bin" / "hdfs").exists():
        return
    tar = None
    for d in tarball_dirs or []:
        hits = list(Path(d).rglob(f"hadoop-{HADOOP_VERSION}.tar.gz"))
        if hits:
            tar = hits[0]
            break
    if tar is None:
        tar = Path(f"/tmp/hadoop-{HADOOP_VERSION}.tar.gz")
        if not tar.exists():
            for url in HADOOP_URLS:
                print("Downloading Hadoop from", url)
                try:
                    sh(f"wget -q -O {tar} {url}", quiet=True)
                    break
                except RuntimeError:
                    tar.unlink(missing_ok=True)
            if not tar.exists():
                raise RuntimeError("Could not download Hadoop. Check that Internet is on.")
    print("Unpacking Hadoop ...")
    sh(f"tar -xzf {tar} -C /opt && mv /opt/hadoop-{HADOOP_VERSION} {HADOOP_HOME}", quiet=True)


def _write_hadoop_conf():
    conf = HADOOP_HOME / "etc" / "hadoop"
    (conf / "core-site.xml").write_text(
        """<?xml version="1.0"?>
<configuration>
  <property><name>fs.defaultFS</name><value>hdfs://localhost:9000</value></property>
  <property><name>hadoop.tmp.dir</name><value>/tmp/hadoop-tmp</value></property>
</configuration>""")
    (conf / "hdfs-site.xml").write_text(
        f"""<?xml version="1.0"?>
<configuration>
  <property><name>dfs.replication</name><value>1</value></property>
  <property><name>dfs.namenode.name.dir</name><value>file://{HDFS_DATA}/name</value></property>
  <property><name>dfs.datanode.data.dir</name><value>file://{HDFS_DATA}/data</value></property>
  <property><name>dfs.permissions.enabled</name><value>false</value></property>
  <property><name>dfs.blocksize</name><value>67108864</value></property>
</configuration>""")
    env_sh = conf / "hadoop-env.sh"
    txt = env_sh.read_text()
    if "T15" not in txt:
        env_sh.write_text(txt + f"\n# T15\nexport JAVA_HOME={os.environ['JAVA_HOME']}\n")


def _port_open(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex(("localhost", port)) == 0


def start_hdfs(tarball_dirs: list[Path] | None = None):
    """Start NameNode + DataNode with `hdfs --daemon` (no SSH needed, works as root)."""
    install_java()
    install_hadoop(tarball_dirs)
    os.environ["HADOOP_HOME"] = str(HADOOP_HOME)
    os.environ["HADOOP_CONF_DIR"] = str(HADOOP_HOME / "etc" / "hadoop")
    os.environ["PATH"] = f"{HADOOP_HOME}/bin:{HADOOP_HOME}/sbin:" + os.environ["PATH"]
    for role in ("NAMENODE", "DATANODE", "SECONDARYNAMENODE"):
        os.environ[f"HDFS_{role}_USER"] = "root"
    _write_hadoop_conf()
    if _port_open(9000):
        print("HDFS already running.")
        return
    if not (HDFS_DATA / "name" / "current").exists():
        sh("hdfs namenode -format -force -nonInteractive", quiet=True)
    sh("hdfs --daemon start namenode", quiet=True)
    sh("hdfs --daemon start datanode", quiet=True)
    for _ in range(60):
        if _port_open(9000):
            break
        time.sleep(1)
    # wait until the DataNode has registered and safe mode is off
    for _ in range(60):
        out = sh("hdfs dfsadmin -report 2>/dev/null | grep 'Live datanodes' || true", check=False, quiet=True)
        if "(1)" in out:
            break
        time.sleep(2)
    sh("hdfs dfsadmin -safemode leave", check=False, quiet=True)
    sh("hdfs dfs -mkdir -p /t15", quiet=True)
    print("HDFS running at hdfs://localhost:9000  (web UI on port 9870)")


def spark_session(cores: int | str = "*", memory: str = "12g", app: str = "t15",
                  hdfs: bool = True):
    install_java()
    install_spark()
    from pyspark.sql import SparkSession

    active = SparkSession.getActiveSession()
    if active is not None:
        active.stop()
    b = (SparkSession.builder.appName(app)
         .master(f"local[{cores}]")
         .config("spark.driver.memory", memory)
         .config("spark.sql.shuffle.partitions", str(max(4, 4 * (cores if isinstance(cores, int) else 4))))
         .config("spark.sql.session.timeZone", "Asia/Kolkata")
         .config("spark.ui.showConsoleProgress", "false"))
    if hdfs:
        b = b.config("spark.hadoop.fs.defaultFS", "hdfs://localhost:9000")
    spark = b.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark


def start(cores: int | str = "*", memory: str = "12g", hdfs: bool = True):
    """One call to get HDFS (optional) and a Spark session."""
    from .config import paths
    p = paths()
    if hdfs:
        try:
            start_hdfs([Path("/kaggle/input")] if p["env"] == "kaggle" else None)
        except Exception as exc:  # keep the team moving if HDFS misbehaves
            print("HDFS failed to start, falling back to local disk:", exc)
            hdfs = False
            os.environ["T15_HDFS"] = f"file://{p['out'] / 'hdfs_fallback'}"
    spark = spark_session(cores=cores, memory=memory, hdfs=hdfs)
    print("Spark", spark.version, "| master", spark.sparkContext.master, "| HDFS" if hdfs else "| local disk")
    return spark


def hdfs_path(name: str) -> str:
    from .config import paths
    return f"{paths()['hdfs_root'].rstrip('/')}/{name}"
