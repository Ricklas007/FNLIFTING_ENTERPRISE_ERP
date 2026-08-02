const os = require('os')

const originalUserInfo = os.userInfo

os.userInfo = function fnliftingSafeUserInfo(options) {
  try {
    return originalUserInfo.call(os, options)
  } catch (error) {
    const infoCode = error && error.info && error.info.code
    const isRecoverableWindowsLookupFailure =
      error && (
        error.code === 'ERR_SYSTEM_ERROR' ||
        error.code === 'ENOMEM' ||
        infoCode === 'ENOMEM'
      )

    if (!isRecoverableWindowsLookupFailure) {
      throw error
    }

    return {
      uid: -1,
      gid: -1,
      username: process.env.USERNAME || process.env.USER || 'fnlifting',
      homedir: process.env.USERPROFILE || process.env.HOME || process.cwd(),
      shell: process.env.COMSPEC || 'cmd.exe',
    }
  }
}
