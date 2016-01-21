#! /usr/bin/env python
# encoding: utf-8
# Harald Klimach 2011
import os

APPNAME = 'aotus'
VERSION = '1'

top = '.'
out = 'build'

def options(opt):
    from waflib.Tools.compiler_fc import fc_compiler
    opt.load('compiler_fc')
    opt.load('compiler_c')
    opt.load('waf_unit_test')
    opt.load('utest_results')
    opt.add_option('--command_sequence', action='store_true', default=False,
                   help='Collect all executed commands into a single file.',
                   dest='cmdsequence')

def configure(conf):
    from waflib import Logs

    # The fcopts provide some sane flag combinations
    # for different variants in the various compilers.
    # They are found in the fc_flags.py in the same
    # directory as the wscript file.
    from fc_flags import fcopts
    # includes options for:
    # * 'warn': activate compile time warnings
    # * 'w2e': turn warnings into errors
    # * 'standard': check for standard compliance
    # * 'debug': activate debugging facilities
    # * 'optimize': turn optimization on
    # * 'profile': activate profiling facilities
    # * 'double': promote default reals to double precision

    # Load the compiler informations
    conf.load('waf_unit_test')

    conf.setenv('cenv',conf.env)
    conf.load('compiler_c')

    conf.setenv('')
    conf.env.DEST_OS = conf.all_envs['cenv'].DEST_OS
    conf.load('compiler_fc')
    conf.check_fortran()

    subconf(conf)

    if getattr(conf.env, 'IFORT_WIN32', False):
      fcname = 'IFORTwin'
    else:
      fcname = conf.env.FC_NAME

    # Flags for the default (production) variant
    conf.env['FCFLAGS'] = ( fcopts[fcname, 'optimize']
                          + fcopts[fcname, 'warn'] )
    conf.env['LINKFLAGS_fcprogram'] = conf.env['FCFLAGS']

    # Set flags for the debugging variant
    # DEBUG Variant
    conf.setenv('debug',conf.env)
    conf.env['FCFLAGS'] = ( fcopts[fcname, 'standard']
                          + fcopts[fcname, 'warn']
                          + fcopts[fcname, 'w2e']
                          + fcopts[fcname, 'debug'] )
    conf.env['LINKFLAGS_fcprogram'] = conf.env['FCFLAGS']

def subconf(conf):
    """
    Configure parts, which are relevant, even when called
    from parent wscripts.
    Useful to restrict parent recursions to just this part
    of the configuration.
    """

    conf.setenv('cenv')

    conf.env.append_unique('DEFINES', ['LUA_ANSI'])

    # Do not change the DEFINES themselves, but use a temporary copy.
    tmpenv = conf.env.derive()
    tmpenv.detach()

    conf.start_msg('Can use POSIX features in Lua')
    conf.check_cc(function_name='mkstemp',
                  header_name=['stdlib.h', 'unistd.h'],
                  define_name='MKSTEMP',
                  mandatory=False)
    conf.check_cc(function_name='popen',
                  header_name=['stdio.h'],
                  define_name='POPEN',
                  mandatory=False)
    conf.check_cc(function_name='srandom',
                  header_name=['stdlib.h', 'math.h'],
                  define_name='SRANDOM',
                  mandatory=False)

    if conf.is_defined('POPEN') and conf.is_defined('MKSTEMP') and conf.is_defined('SRANDOM'):
      conf.env = tmpenv
      conf.all_envs['cenv'].DEFINES_LUA_POSIX = ['LUA_USE_POSIX']
      conf.end_msg('yes')
    else:
      conf.env = tmpenv
      conf.end_msg('NO')

    # Only required to build the Lua interpreter
    conf.check_cc(lib='m', uselib_store='MATH', mandatory=False)

    conf.setenv('')

    conf.check_fc(fragment = '''
       program check_iso_c
         use, intrinsic :: iso_c_binding
         implicit none
         write(*,*) c_int
       end program check_iso_c''',
                  msg = "Checking for ISO_C_Binding support",
                  mandatory = 'true')

    tmpenv = conf.env.derive()
    tmpenv.detach()

    conf.start_msg('Checking for Quadruple precision')
    conf.check_fc(fragment = '''
       program checkquad
         implicit none
         integer, parameter :: quad_k = selected_real_kind(33)
         real(kind=quad_k) :: a_quad_real
         write(*,*) quad_k
       end program checkquad''',
                  mandatory=False, define_name='quadruple',
                  execute = True, define_ret = True)

    tmpenv['quad_support'] = conf.is_defined('quadruple')
    if tmpenv['quad_support']:
       conf.env['quad_k'] = int(conf.get_define('quadruple').replace('"', '').strip())
       if conf.env['quad_k'] < 1:
          tmpenv['quad_support'] = False
    if tmpenv['quad_support']:
       conf.end_msg('yes', color='GREEN')
    else:
       conf.end_msg('NO', color='RED')

    conf.start_msg('Checking for extended double precision')
    conf.check_fc(fragment = '''
       program checkxdble
         implicit none
         integer, parameter :: xdble_k = selected_real_kind(18)
         real(kind=xdble_k) :: a_xdble_real
         write(*,*) xdble_k
       end program checkxdble''',
                  mandatory=False, define_name='extdouble',
                  execute = True, define_ret = True)

    tmpenv['xdble_support'] = False
    if conf.is_defined('extdouble'):
       conf.env['xdble_k'] = int(conf.get_define('extdouble').replace('"', '').strip())
       if conf.env['xdble_k'] > 0 and conf.env['xdble_k'] != conf.env['quad_k']:
          tmpenv['xdble_support'] = True

    if tmpenv['xdble_support']:
       conf.end_msg('yes', color='GREEN')
    else:
       conf.end_msg('NO', color='RED')

    conf.env = tmpenv


def build(bld):
    if bld.options.cmdsequence:
        import waflib.extras.command_sequence

    core_sources = ['external/lua-5.3.2/src/lapi.c',
                    'external/lua-5.3.2/src/lcode.c',
                    'external/lua-5.3.2/src/lctype.c',
                    'external/lua-5.3.2/src/ldebug.c',
                    'external/lua-5.3.2/src/ldo.c',
                    'external/lua-5.3.2/src/ldump.c',
                    'external/lua-5.3.2/src/lfunc.c',
                    'external/lua-5.3.2/src/lgc.c',
                    'external/lua-5.3.2/src/llex.c',
                    'external/lua-5.3.2/src/lmem.c',
                    'external/lua-5.3.2/src/lobject.c',
                    'external/lua-5.3.2/src/lopcodes.c',
                    'external/lua-5.3.2/src/lparser.c',
                    'external/lua-5.3.2/src/lstate.c',
                    'external/lua-5.3.2/src/lstring.c',
                    'external/lua-5.3.2/src/ltable.c',
                    'external/lua-5.3.2/src/ltm.c',
                    'external/lua-5.3.2/src/lundump.c',
                    'external/lua-5.3.2/src/lvm.c',
                    'external/lua-5.3.2/src/lzio.c']
    lib_sources = ['external/lua-5.3.2/src/lauxlib.c',
                   'external/lua-5.3.2/src/lbaselib.c',
                   'external/lua-5.3.2/src/lbitlib.c',
                   'external/lua-5.3.2/src/lcorolib.c',
                   'external/lua-5.3.2/src/ldblib.c',
                   'external/lua-5.3.2/src/liolib.c',
                   'external/lua-5.3.2/src/lmathlib.c',
                   'external/lua-5.3.2/src/loslib.c',
                   'external/lua-5.3.2/src/ltablib.c',
                   'external/lua-5.3.2/src/lstrlib.c',
                   'external/lua-5.3.2/src/lutf8lib.c',
                   'external/lua-5.3.2/src/loadlib.c',
                   'external/lua-5.3.2/src/linit.c']
    lua_sources = ['external/lua-5.3.2/src/lua.c']
    luac_sources = ['external/lua-5.3.2/src/luac.c']

    wrap_sources = ['LuaFortran/wrap_lua_dump.c']

    flu_sources = ['LuaFortran/lua_fif.f90',
                   'LuaFortran/dump_lua_fif_module.f90',
                   'LuaFortran/lua_parameters.f90',
                   'LuaFortran/flu_binding.f90']

    aotus_sources = ['source/aotus_module.f90',
                     'source/aot_err_module.f90',
                     'source/aot_fun_module.f90',
                     'source/aot_fun_declaration_module.f90',
                     'source/aot_kinds_module.f90',
                     'source/aot_table_module.f90',
                     'source/aot_table_ops_module.f90',
                     'source/aot_top_module.f90',
		     'source/aot_out_module.f90',
		     'source/aot_out_general_module.f90',
                     'source/aot_path_module.f90',
                     'source/aot_vector_module.f90']

    # C parts
    bld(
        features = 'c',
        source = core_sources + lib_sources,
        use = ['LUA_POSIX'],
        target = 'luaobjs')

    bld(
        features = 'c cstlib',
        use = 'luaobjs',
        target = 'lualib')

    bld(
        features = 'c',
        source = wrap_sources,
        use = 'luaobjs',
        includes = 'external/lua-5.3.2/src',
        target = 'wrapobjs')

    ## Building the lua interpreter (usually not needed).
    ## Only built if libm available.
    if 'LIB_MATH' in bld.env:
      bld(
          features = 'c cprogram',
          use = ['lualib', 'MATH'],
          source = lua_sources,
          target = 'lua')


    # Fortran parts
    if bld.env['quad_support']:
        aotus_sources += ['source/quadruple/aot_quadruple_fun_module.f90']
        aotus_sources += ['source/quadruple/aot_quadruple_table_module.f90']
        aotus_sources += ['source/quadruple/aot_quadruple_top_module.f90']
        aotus_sources += ['source/quadruple/aot_quadruple_out_module.f90']
        aotus_sources += ['source/quadruple/aot_quadruple_vector_module.f90']
    else:
        aotus_sources += ['source/quadruple/dummy_quadruple_fun_module.f90']
        aotus_sources += ['source/quadruple/dummy_quadruple_table_module.f90']
        aotus_sources += ['source/quadruple/dummy_quadruple_top_module.f90']
        aotus_sources += ['source/quadruple/dummy_quadruple_out_module.f90']
        aotus_sources += ['source/quadruple/dummy_quadruple_vector_module.f90']

    if bld.env['xdble_support']:
        aotus_sources += ['source/extdouble/aot_extdouble_fun_module.f90']
        aotus_sources += ['source/extdouble/aot_extdouble_table_module.f90']
        aotus_sources += ['source/extdouble/aot_extdouble_top_module.f90']
        aotus_sources += ['source/extdouble/aot_extdouble_out_module.f90']
        aotus_sources += ['source/extdouble/aot_extdouble_vector_module.f90']
    else:
        aotus_sources += ['source/extdouble/dummy_extdouble_fun_module.f90']
        aotus_sources += ['source/extdouble/dummy_extdouble_table_module.f90']
        aotus_sources += ['source/extdouble/dummy_extdouble_top_module.f90']
        aotus_sources += ['source/extdouble/dummy_extdouble_out_module.f90']
        aotus_sources += ['source/extdouble/dummy_extdouble_vector_module.f90']

    bld(
        features = 'fc',
        source = flu_sources,
        target = 'fluobjs')

    bld(
        features = 'fc fcstlib',
        use = ['luaobjs', 'fluobjs', 'wrapobjs'],
        target = 'flu')

    bld(
        features = 'fc fcstlib',
        source = aotus_sources,
        use = ['luaobjs', 'fluobjs', 'wrapobjs'],
        target = 'aotus')

    bld(
        features = 'fc fcprogram',
        source = ['sample/aotus_sample.f90'],
        use = 'aotus',
        target = 'aotus_sample')

    bld(
        features = 'fc fcprogram',
        source = ['LuaFortran/examples/test.f90'],
        use = 'flu',
        target = 'flu_sample')

    from waflib.extras import utest_results
    utest_results.utests(bld, 'aotus')
    if bld.env['quad_support']:
        utest_results.utests(bld, use = 'aotus', path = 'utests/quadruple')
    bld.add_post_fun(utest_results.summary)

    # install_files actually only done, if in install mode.
    # However, the if here avoids the ant_glob in the build directory
    # to be run if not in the install phase...
    if bld.cmd == 'install':
        bld.install_files('${PREFIX}/include',
                          bld.path.get_bld().ant_glob('*.mod'))
        bld.install_files('${PREFIX}/lib', 'libaotus.a')


from waflib.Build import BuildContext
from waflib import Utils, TaskGen

# Modify Fortran tasks to not contain SHLIB and STLIB markers if not
# explicitly requested.
@TaskGen.feature('fcprogram', 'fcshlib', 'fcstlib')
@TaskGen.before_method('process_use')
@TaskGen.after_method('apply_link')
def kill_marker_flags(self):
  if not self.env.LIB and not self.env.LIBPATH:
    self.env.FCSHLIB_MARKER = []
  if not self.env.STLIB and not self.env.STLIBPATH:
    self.env.FCSTLIB_MARKER = []

# Modifiy C tasks to use a dedicated C environment.
@TaskGen.feature('c', 'cstlib', 'cprogram')
@TaskGen.before('process_rule')
def enter_cenv(self):
  self.env = self.bld.all_envs['cenv'].derive()

# A class to describe the debug variant
class debug(BuildContext):
    "Build a debug executable"
    cmd = 'debug'
    variant = 'debug'
