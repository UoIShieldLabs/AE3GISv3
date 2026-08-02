
export type ContainerType =
  | 'web-server'
  | 'file-server'
  | 'plc'
  | 'firewall'
  | 'switch'
  | 'router'
  | 'workstation'
  | 'hmi'
  | 'directory'
  | 'ids'
  | 'siem'
  | 'database'
  | 'pcap'
  | 'bastion' 
  | 'proxy'
  | 'internal-dns'
  | 'external-dns'
  | 'dhcp';

export const typeOptions = [
  { value: 'router', label: 'Router' },
  { value: 'firewall', label: 'Firewall' },
  { value: 'switch', label: 'Switch' },
  { value: 'web-server', label: 'Web Server' },
  { value: 'file-server', label: 'File Server' },
  { value: 'plc', label: 'PLC' },
  { value: 'workstation', label: 'Workstation' },
  { value: 'hmi', label: 'HMI' },
  { value: 'database', label: 'Database' },
  { value: 'directory', label: 'Directory' },
  { value: 'ids', label: 'IDS' },
  { value: 'siem', label: 'SIEM' },
  { value: 'pcap', label: 'Packet Capture' },
  { value: 'bastion', label: 'Bastion' },
  { value: 'proxy', label: 'Proxy' },
  { value: 'internal-dns', label: 'Internal DNS' },
  { value: 'external-dns', label: 'External DNS' },
  { value: 'dhcp', label: 'DHCP' },
];

export const typeColors: Record<ContainerType, string> = {
  'router': '#ff00ff',
  'firewall': '#ff3344',
  'switch': '#ffaa00',
  'web-server': '#00ff9f',
  'file-server': '#00d4ff',
  'plc': '#ffaa00',
  'workstation': '#4466ff',
  'hmi': '#33ccff',
  'directory': '#240177',
  'ids': '#240177',
  'siem': '#240177',
  'database': '#240177',
  'pcap': '#240177',
  'bastion': '#240177',
  'proxy': '#240177',
  'internal-dns': '#240177',
  'external-dns': '#240177',
  'dhcp': '#240177'
};

export const typeLabels: Record<ContainerType, string> = {
  'router': 'RTR',
  'firewall': 'FW',
  'switch': 'SW',
  'web-server': 'WEB',
  'file-server': 'FS',
  'plc': 'PLC',
  'workstation': 'WS',
  'hmi': 'HMI',
  'directory':   'DIR',
  'ids':         'IDS',
  'siem':        'SIEM',
  'database':    'DB',
  'pcap':        'PCAP',
  'bastion':     'BS',
  'proxy':       'PRX',
  'internal-dns':'IDNS',
  'external-dns':'EDNS',
  'dhcp':        'DHCP'
};

export const typeDisplayNames: Record<string, string> = {
  'web-server': 'Web Server',
  'file-server': 'File Server',
  'plc': 'PLC Controller',
  'firewall': 'Firewall',
  'switch': 'Network Switch',
  'router': 'Router',
  'workstation': 'Workstation',
  'hmi': 'HMI',
  'directory': 'Directory',
  'ids': 'IDS',
  'siem': 'SIEM',
  'database': 'Database',
  'pcap': 'PCAP',
  'bastion': 'Bastion',
  'proxy': 'Proxy',
  'internal-dns': 'Internal DNS',
  'external-dns': 'External DNS',
  'dhcp': "DHCP"
};