# Distributed under the OSI-approved BSD 3-Clause License.  See accompanying
# file Copyright.txt or https://cmake.org/licensing for details.

cmake_minimum_required(VERSION 3.5)

file(MAKE_DIRECTORY
  "/home/valery/Documents/MyBHuman/MyBuman/Make/CMake"
  "/home/valery/Documents/MyBHuman/MyBuman/build/Booster-prefix/src/Booster-build"
  "/home/valery/Documents/MyBHuman/MyBuman/build/Booster-prefix"
  "/home/valery/Documents/MyBHuman/MyBuman/build/Booster-prefix/tmp"
  "/home/valery/Documents/MyBHuman/MyBuman/build/Booster-prefix/src/Booster-stamp"
  "/home/valery/Documents/MyBHuman/MyBuman/build/Booster-prefix/src"
  "/home/valery/Documents/MyBHuman/MyBuman/build/Booster-prefix/src/Booster-stamp"
)

set(configSubDirs Debug;Develop;Release)
foreach(subDir IN LISTS configSubDirs)
    file(MAKE_DIRECTORY "/home/valery/Documents/MyBHuman/MyBuman/build/Booster-prefix/src/Booster-stamp/${subDir}")
endforeach()
if(cfgdir)
  file(MAKE_DIRECTORY "/home/valery/Documents/MyBHuman/MyBuman/build/Booster-prefix/src/Booster-stamp${cfgdir}") # cfgdir has leading slash
endif()
