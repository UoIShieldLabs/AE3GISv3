// Commands that stream a live capture into a local tool. The backend serves
// the pcap as it grows (?follow=true), so Wireshark reads it like an
// interface: `-k` starts capturing at once, `-i -` reads stdin.

export type Platform = 'mac' | 'linux' | 'windows';

export function detectPlatform(userAgent: string = typeof navigator === 'undefined' ? '' : navigator.userAgent): Platform {
  if (/Windows/i.test(userAgent)) return 'windows';
  if (/Mac OS X|Macintosh/i.test(userAgent)) return 'mac';
  return 'linux';
}

const quote = (url: string, platform: Platform) => (platform === 'windows' ? `"${url}"` : `'${url}'`);

export function wiresharkCommand(url: string, platform: Platform): string {
  const src = platform === 'windows' ? `curl.exe -sN ${quote(url, platform)}` : `curl -sN ${quote(url, platform)}`;
  switch (platform) {
    case 'mac':
      return `${src} | /Applications/Wireshark.app/Contents/MacOS/Wireshark -k -i -`;
    case 'windows':
      return `${src} | & "C:\\Program Files\\Wireshark\\Wireshark.exe" -k -i -`;
    default:
      return `${src} | wireshark -k -i -`;
  }
}

export function tcpdumpCommand(url: string, platform: Platform): string {
  const src = platform === 'windows' ? `curl.exe -sN ${quote(url, platform)}` : `curl -sN ${quote(url, platform)}`;
  return `${src} | tcpdump -nn -r -`;
}
