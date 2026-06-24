# =============================================================================
# Cell 01 — Setup: Dependencies, JDK, Gradle
# =============================================================================
# Installs all required Python packages, patches sqlite3 for ChromaDB
# compatibility, installs JDK and Gradle 8.7, and configures PATH.
# This is the ONLY cell that uses ! shell commands.
# =============================================================================

# --- Python dependencies ---
!pip install -q openai chromadb langfuse tavily-python pyyaml pysqlite3-binary

# --- SQLite3 override for ChromaDB compatibility in Colab ---
# ChromaDB requires a newer SQLite3 than Colab ships by default.
# pysqlite3-binary provides a compatible version.
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

# --- Install JDK (headless) ---
!apt-get update -qq && apt-get install -y -qq default-jdk-headless > /dev/null 2>&1

# --- Install Gradle 8.7 ---
!wget -q https://services.gradle.org/distributions/gradle-8.7-bin.zip && unzip -q -o gradle-8.7-bin.zip -d /opt/ > /dev/null 2>&1

# --- Configure environment variables ---
import os

os.environ['JAVA_HOME'] = '/usr/lib/jvm/default-java'
os.environ['GRADLE_HOME'] = '/opt/gradle-8.7'
os.environ['PATH'] = f"/opt/gradle-8.7/bin:{os.environ['JAVA_HOME']}/bin:{os.environ['PATH']}"

# --- Verification ---
print("=" * 60)
print("✅ Dependencias Python instaladas correctamente")
print(f"✅ JAVA_HOME = {os.environ['JAVA_HOME']}")
print(f"✅ GRADLE_HOME = {os.environ['GRADLE_HOME']}")
print("✅ JDK y Gradle 8.7 instalados y configurados en PATH")
print("✅ SQLite3 parcheado para compatibilidad con ChromaDB")
print("=" * 60)
