import subprocess
from os.path import dirname, join as os_path_join, isfile

class StFlash:
    
    def __init__(self) -> None:
        self._set_st_flash_path()
        self.erase_flash = [
            self.stflash_exe,
            "--connect-under-reset",
            "--reset",
            "erase"]
        self.reset = [
            self.stflash_exe,
            "--connect-under-reset",
            "reset"]
        self.process_return = subprocess.CalledProcessError([], 0)
        self._last_cmd = None

    def write(self, bin_path: str):
        if not isfile(bin_path):
            self.process_return = subprocess.CalledProcessError(
                returncode=-1,
                cmd=None)
            self.process_return.stdout = [bin_path]
            self.process_return.stderr = ['Invalid file path']
            return self.process_return
        self._set_command(bin_path)
        self._send_reset_command()
        if self._process_rise_error():
            return self.process_return
        self._send_erase_command()
        if self._process_rise_error():
            return self.process_return
        self._send_write_command()
        return self.process_return

    def get_std_out(self):
        self.process_return.stdout = self._clean_std_output(self.process_return.stdout)
        self.process_return.stderr = self._clean_std_output(self.process_return.stderr)

        max_size = len(self.process_return.stdout)
        if max_size == 0:
            std_out = []
        else:
            std_out = self.process_return.stdout[0::max(1,max_size-1)]

        max_size = len(self.process_return.stderr)
        if max_size == 0:
            std_out = std_out + [
                'Command: '
                + str(self._last_cmd)]
        else:
            std_out = std_out + [
                self.process_return.stderr[-1],
                'Command: '
                + str(self._last_cmd)]
        return std_out

    def _set_st_flash_path(self):
        module_dir = dirname(__file__)
        self.stflash_exe = os_path_join(
            module_dir,
            "st-flash.exe")

    def _set_command(self, bin_path):
        self.flash_firmware = [
            self.stflash_exe,
            "--connect-under-reset",
            "--reset",
            "write",
            bin_path,
            "0x8000000"]

    def _send_command(self, cmd, timeout=None, retry=2):
        self._last_cmd = cmd
        try:
            self.process_return = subprocess.run(
                cmd,
                capture_output=True,
                timeout=timeout,
                check=True)
        except Exception as exc:
            if retry > 0:
                print('\t\t'
                      f'Retry of {cmd}')
                self._send_command(cmd, timeout=timeout, retry=retry-1)
            else:
                self.process_return = exc

    def _send_reset_command(self):
        print("\treset µC")
        self._send_command(self.reset, timeout=1, retry=5)

    def _send_erase_command(self):
        print("\terase flash")
        self._send_command(self.erase_flash, timeout=5)

    def _send_write_command(self):
        print("\tflash firmware")
        self._send_command(self.flash_firmware, timeout=60, retry=1)

    def _process_rise_error(self):
        if isinstance(self.process_return, subprocess.SubprocessError):
            return True
        else:
            return False

    def _clean_std_output(self, std_output):
        if isinstance(std_output, bytes):
            std_output = std_output.decode(errors='ignore')
            while '\r' in std_output:
                std_output = std_output.replace('\r', '')
            std_output = std_output.split('\n')
            
            while '' in std_output:
                std_output.remove('')
        return std_output
        

if __name__ == "__main__":
    import time
    st_flash = StFlash()
    bin_path = "C:\\Projets\\BMS3\\BMS3_dev\\dev\\BMS_3.0\\BUILD\\BMS3_STM32052x8\\ARMC6\\bin\\v02.01\\BMS_3.0_v3_v02.01_dark_rainbow.bin"
    for _ in range(20):
        start = time.time()
        process_return = st_flash.write(bin_path)

        if isinstance(process_return, subprocess.SubprocessError):
            print(st_flash.get_std_out())
        print(f'Time elapse: {time.time()-start} s.')
        input("\nPress a key to continu...")

    # Ajouter un reset entre les commandes
    