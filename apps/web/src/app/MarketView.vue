<script setup lang="ts">
import * as echarts from 'echarts';
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue';
import type { components } from '@stock-research/api-types';

import { http } from '../api/client';

type MarketSnapshotSummary = components['schemas']['MarketSnapshotSummaryResponse'];
type MarketSnapshot = components['schemas']['MarketSnapshotResponse'];
type MarketBar = components['schemas']['MarketBarResponse'];
type MarketIndicator = components['schemas']['MarketIndicatorResponse'];
type IndicatorProfile = { name: string; config: IndicatorConfig };
type ChartTheme = 'light' | 'dark' | 'cool' | 'warm' | 'contrast' | 'custom';
type ProfileBackup = {
  profiles: IndicatorProfile[];
  defaultProfileName: string;
  current: IndicatorConfig;
};
type UserSettingResponse = components['schemas']['UserSettingResponse'];
type ConflictRecord = {
  id: string;
  time: string;
  action: 'local' | 'cloud' | 'merge';
  localOnly: string[];
  cloudOnly: string[];
  conflicting: string[];
  defaultSource: string;
};

const symbols = ref<string[]>(['600519.SH', '000001.SZ']);
const symbolInput = ref('');
const selectedSymbol = ref('600519.SH');
const summaries = ref<Record<string, MarketSnapshotSummary>>({});
const snapshots = ref<MarketSnapshot[]>([]);
const bars = ref<MarketBar[]>([]);
const indicators = ref<MarketIndicator[]>([]);
const period = ref('1m');
const rsiPeriod = ref(14);
const macdFast = ref(12);
const macdSlow = ref(26);
const macdSignal = ref(9);
const showMa = ref(true);
const showEma = ref(true);
const showVolumeMa = ref(true);
const showMacd = ref(true);
const showRsi = ref(true);
const theme = ref<ChartTheme>('light');
const customBackground = ref('#ffffff');
const customText = ref('#111827');
const conflictPolicy = ref<'ask' | 'local' | 'cloud' | 'merge'>('ask');
const profiles = ref<IndicatorProfile[]>([]);
const profileName = ref('');
const defaultProfileName = ref('');
const cloudUpdatedAt = ref<string | null>(null);
const localDirty = ref(false);
const pendingCloudBackup = ref<ProfileBackup | null>(null);
const pendingCloudUpdatedAt = ref('');
const conflictHistory = ref<ConflictRecord[]>([]);
const archivedConflictHistory = ref<ConflictRecord[]>([]);
const showArchive = ref(false);
const conflictCleanupPolicy = ref<'none' | 'trim' | 'archive'>('none');
const conflictHistoryLimit = ref(100);
const archiveCleanupPolicy = ref<'none' | 'trim'>('none');
const archiveHistoryLimit = ref(200);

const mergePreview = computed(() => {
  const cloud = pendingCloudBackup.value;
  if (!cloud) {
    return null;
  }
  const localNames = new Set(profiles.value.map((profile) => profile.name));
  const cloudNames = new Set(cloud.profiles.map((profile) => profile.name));
  const localOnly = profiles.value
    .filter((profile) => !cloudNames.has(profile.name))
    .map((profile) => profile.name);
  const cloudOnly = cloud.profiles
    .filter((profile) => !localNames.has(profile.name))
    .map((profile) => profile.name);
  const conflicting = cloud.profiles
    .filter((profile) => localNames.has(profile.name))
    .map((profile) => profile.name);
  const defaultSource = defaultProfileName.value
    ? '本地'
    : cloud.defaultProfileName
      ? '云端'
      : '无';
  return { localOnly, cloudOnly, conflicting, defaultSource };
});
const error = ref('');
const loading = ref(false);
const status = ref<'loading' | 'ok' | 'error'>('loading');
const chartRef = ref<HTMLDivElement | null>(null);

let chart: ReturnType<typeof echarts.init> | null = null;
let refreshTimer: number | undefined;

const STORAGE_KEY = 'stock-research.indicator-config.v1';
const PROFILES_KEY = 'stock-research.indicator-profiles.v1';
const DEFAULT_PROFILE_KEY = 'stock-research.indicator-default-profile.v1';
const CONFLICT_HISTORY_KEY = 'stock-research.indicator-conflict-history.v1';
const CONFLICT_ARCHIVE_KEY = 'stock-research.indicator-conflict-archive.v1';
const CLEANUP_SETTINGS_KEY = 'stock-research.indicator-conflict-cleanup.v1';

const indicatorPresets = {
  default: { rsiPeriod: 14, macdFast: 12, macdSlow: 26, macdSignal: 9 },
  short: { rsiPeriod: 6, macdFast: 6, macdSlow: 13, macdSignal: 5 },
  long: { rsiPeriod: 24, macdFast: 24, macdSlow: 52, macdSignal: 18 },
  ultraShort: { rsiPeriod: 3, macdFast: 3, macdSlow: 6, macdSignal: 2 },
  swing: { rsiPeriod: 14, macdFast: 10, macdSlow: 22, macdSignal: 7 },
  trend: { rsiPeriod: 21, macdFast: 18, macdSlow: 42, macdSignal: 12 },
} as const;

type IndicatorPresetName = keyof typeof indicatorPresets;

function currentThemeColors(): { background: string; text: string } {
  if (theme.value === 'custom') {
    return { background: customBackground.value, text: customText.value };
  }
  const themes: Record<Exclude<ChartTheme, 'custom'>, { background: string; text: string }> = {
    light: { background: '#ffffff', text: '#111827' },
    dark: { background: '#111827', text: '#e5e7eb' },
    cool: { background: '#f0f9ff', text: '#1e3a8a' },
    warm: { background: '#fff7ed', text: '#7c2d12' },
    contrast: { background: '#000000', text: '#ffffff' },
  };
  return themes[theme.value];
}

function parseSymbols(input: string): string[] {
  return input
    .split(/[\s,，]+/)
    .map((item) => item.trim().toUpperCase())
    .filter(Boolean);
}

function addSymbols(): void {
  for (const symbol of parseSymbols(symbolInput.value)) {
    if (!symbols.value.includes(symbol)) {
      symbols.value.push(symbol);
    }
  }
  symbolInput.value = '';
  if (!symbols.value.includes(selectedSymbol.value)) {
    selectedSymbol.value = symbols.value[0] ?? '';
  }
  void refreshAll();
}

function removeSymbol(symbol: string): void {
  symbols.value = symbols.value.filter((item) => item !== symbol);
  delete summaries.value[symbol];
  if (selectedSymbol.value === symbol) {
    selectedSymbol.value = symbols.value[0] ?? '';
  }
  if (symbols.value.length > 0) {
    void refreshAll();
  } else {
    snapshots.value = [];
    bars.value = [];
    renderChart();
  }
}

function selectSymbol(symbol: string): void {
  selectedSymbol.value = symbol;
  void refreshAll();
}

async function loadSummaries(): Promise<void> {
  if (symbols.value.length === 0) {
    summaries.value = {};
    return;
  }

  const responses = await Promise.all(
    symbols.value.map(async (symbol) => {
      const { data } = await http.get<MarketSnapshotSummary>(
        `/market/snapshots/${encodeURIComponent(symbol)}/summary`,
      );
      return [symbol, data] as const;
    }),
  );

  const next: Record<string, MarketSnapshotSummary> = {};
  for (const [symbol, summary] of responses) {
    next[symbol] = summary;
  }
  summaries.value = next;
}

async function loadSnapshots(): Promise<void> {
  if (!selectedSymbol.value) {
    snapshots.value = [];
    return;
  }
  const { data } = await http.get<MarketSnapshot[]>(
    `/market/snapshots/${encodeURIComponent(selectedSymbol.value)}?limit=20`,
  );
  snapshots.value = data;
}

async function loadBars(): Promise<void> {
  if (!selectedSymbol.value) {
    bars.value = [];
    return;
  }
  const { data } = await http.get<MarketBar[]>(
    `/market/bars/${encodeURIComponent(selectedSymbol.value)}?period=${encodeURIComponent(period.value)}&limit=100`,
  );
  bars.value = data;
}

async function loadIndicators(): Promise<void> {
  if (!selectedSymbol.value) {
    indicators.value = [];
    return;
  }
  const { data } = await http.get<MarketIndicator[]>(
    `/market/bars/${encodeURIComponent(selectedSymbol.value)}/indicators?period=${encodeURIComponent(period.value)}&limit=100&rsi_period=${rsiPeriod.value}&macd_fast=${macdFast.value}&macd_slow=${macdSlow.value}&macd_signal=${macdSignal.value}`,
  );
  indicators.value = data;
}

async function refreshAll(): Promise<void> {
  loading.value = true;
  status.value = 'loading';
  error.value = '';
  try {
    await Promise.all([loadSummaries(), loadSnapshots(), loadBars(), loadIndicators()]);
    await nextTick();
    renderChart();
    status.value = 'ok';
  } catch {
    error.value = '行情加载失败，请确认标的代码或稍后重试';
    status.value = 'error';
  } finally {
    loading.value = false;
  }
}

function setPeriod(nextPeriod: string): void {
  period.value = nextPeriod;
  saveConfig();
  void refreshAll();
}

function applyIndicatorConfig(): void {
  saveConfig();
  void refreshAll();
}

function applyPreset(name: IndicatorPresetName): void {
  const preset = indicatorPresets[name];
  rsiPeriod.value = preset.rsiPeriod;
  macdFast.value = preset.macdFast;
  macdSlow.value = preset.macdSlow;
  macdSignal.value = preset.macdSignal;
  saveConfig();
  void refreshAll();
}

type IndicatorConfig = {
  period: string;
  rsiPeriod: number;
  macdFast: number;
  macdSlow: number;
  macdSignal: number;
  showMa: boolean;
  showEma: boolean;
  showVolumeMa: boolean;
  showMacd: boolean;
  showRsi: boolean;
  theme: ChartTheme;
  customBackground: string;
  customText: string;
  conflictPolicy: 'ask' | 'local' | 'cloud' | 'merge';
};

function buildConfigObject(): IndicatorConfig {
  return {
    period: period.value,
    rsiPeriod: rsiPeriod.value,
    macdFast: macdFast.value,
    macdSlow: macdSlow.value,
    macdSignal: macdSignal.value,
    showMa: showMa.value,
    showEma: showEma.value,
    showVolumeMa: showVolumeMa.value,
    showMacd: showMacd.value,
    showRsi: showRsi.value,
    theme: theme.value,
    customBackground: customBackground.value,
    customText: customText.value,
    conflictPolicy: conflictPolicy.value,
  };
}

function buildBackupObject(): ProfileBackup {
  return {
    profiles: profiles.value,
    defaultProfileName: defaultProfileName.value,
    current: buildConfigObject(),
  };
}

function applyConfigObject(parsed: Partial<IndicatorConfig>): void {
  if (typeof parsed.period === 'string') period.value = parsed.period;
  if (typeof parsed.rsiPeriod === 'number') rsiPeriod.value = parsed.rsiPeriod;
  if (typeof parsed.macdFast === 'number') macdFast.value = parsed.macdFast;
  if (typeof parsed.macdSlow === 'number') macdSlow.value = parsed.macdSlow;
  if (typeof parsed.macdSignal === 'number') macdSignal.value = parsed.macdSignal;
  if (typeof parsed.showMa === 'boolean') showMa.value = parsed.showMa;
  if (typeof parsed.showEma === 'boolean') showEma.value = parsed.showEma;
  if (typeof parsed.showVolumeMa === 'boolean') showVolumeMa.value = parsed.showVolumeMa;
  if (typeof parsed.showMacd === 'boolean') showMacd.value = parsed.showMacd;
  if (typeof parsed.showRsi === 'boolean') showRsi.value = parsed.showRsi;
  if (
    parsed.theme === 'light' ||
    parsed.theme === 'dark' ||
    parsed.theme === 'cool' ||
    parsed.theme === 'warm' ||
    parsed.theme === 'contrast' ||
    parsed.theme === 'custom'
  ) {
    theme.value = parsed.theme;
  }
  if (typeof parsed.customBackground === 'string') {
    customBackground.value = parsed.customBackground;
  }
  if (typeof parsed.customText === 'string') {
    customText.value = parsed.customText;
  }
  if (
    parsed.conflictPolicy === 'ask' ||
    parsed.conflictPolicy === 'local' ||
    parsed.conflictPolicy === 'cloud' ||
    parsed.conflictPolicy === 'merge'
  ) {
    conflictPolicy.value = parsed.conflictPolicy;
  }
}

function loadConfig(): void {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return;
    }
    applyConfigObject(JSON.parse(raw) as Partial<IndicatorConfig>);
  } catch {
    window.localStorage.removeItem(STORAGE_KEY);
  }
}

function saveConfig(): void {
  localDirty.value = true;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(buildConfigObject()));
}

function exportConfig(): void {
  const blob = new Blob([JSON.stringify(buildConfigObject(), null, 2)], {
    type: 'application/json',
  });
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'stock-research-indicator-config.json';
  anchor.click();
  window.URL.revokeObjectURL(url);
}

function importConfig(event: Event): void {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) {
    return;
  }

  const reader = new FileReader();
  reader.onload = () => {
    try {
      applyConfigObject(JSON.parse(String(reader.result)) as Partial<IndicatorConfig>);
      saveConfig();
      void refreshAll();
    } catch {
      error.value = '配置文件解析失败';
    } finally {
      input.value = '';
    }
  };
  reader.readAsText(file);
}

function exportProfilesBackup(): void {
  const backup = buildBackupObject();
  const blob = new Blob([JSON.stringify(backup, null, 2)], {
    type: 'application/json',
  });
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'stock-research-indicator-profiles.json';
  anchor.click();
  window.URL.revokeObjectURL(url);
}

function importProfilesBackup(event: Event): void {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) {
    return;
  }

  const reader = new FileReader();
  reader.onload = () => {
    try {
      const backup = JSON.parse(String(reader.result)) as Partial<ProfileBackup>;
      if (Array.isArray(backup.profiles)) {
        profiles.value = backup.profiles as IndicatorProfile[];
      }
      if (typeof backup.defaultProfileName === 'string') {
        defaultProfileName.value = backup.defaultProfileName;
      }
      if (backup.current) {
        applyConfigObject(backup.current);
      }
      persistProfiles();
      persistDefaultProfileName();
      saveConfig();
      void refreshAll();
    } catch {
      error.value = '方案备份解析失败';
    } finally {
      input.value = '';
    }
  };
  reader.readAsText(file);
}

const CLOUD_SETTING_KEY = 'indicator_profiles';

async function syncToCloud(): Promise<void> {
  if (cloudUpdatedAt.value && localDirty.value) {
    const confirmed = window.confirm('本地配置有未同步修改，确定覆盖云端配置吗？');
    if (!confirmed) {
      return;
    }
  }
  try {
    const { data } = await http.put<UserSettingResponse>(`/user-settings/${CLOUD_SETTING_KEY}`, {
      value: buildBackupObject(),
    });
    cloudUpdatedAt.value = data.updated_at;
    localDirty.value = false;
  } catch {
    error.value = '云端同步失败';
  }
}

function applyBackup(backup: ProfileBackup): void {
  profiles.value = backup.profiles;
  defaultProfileName.value = backup.defaultProfileName;
  applyConfigObject(backup.current);
  persistProfiles();
  persistDefaultProfileName();
  saveConfig();
  void refreshAll();
}

function applyMergedBackup(cloud: ProfileBackup): void {
  const merged = [...profiles.value];
  for (const cloudProfile of cloud.profiles) {
    if (!merged.some((profile) => profile.name === cloudProfile.name)) {
      merged.push(cloudProfile);
    }
  }
  profiles.value = merged;
  if (!defaultProfileName.value && cloud.defaultProfileName) {
    defaultProfileName.value = cloud.defaultProfileName;
  }
  persistProfiles();
  persistDefaultProfileName();
  saveConfig();
  void refreshAll();
}

function resolveCloudConflict(action: 'local' | 'cloud' | 'merge'): void {
  const backup = pendingCloudBackup.value;
  if (!backup) {
    return;
  }
  const preview = mergePreview.value;
  conflictHistory.value.unshift({
    id: `${Date.now()}-${conflictHistory.value.length}`,
    time: new Date().toLocaleString('zh-CN'),
    action,
    localOnly: preview?.localOnly ?? [],
    cloudOnly: preview?.cloudOnly ?? [],
    conflicting: preview?.conflicting ?? [],
    defaultSource: preview?.defaultSource ?? '无',
  });
  persistConflictHistory();
  if (action === 'cloud') {
    applyBackup(backup);
    cloudUpdatedAt.value = pendingCloudUpdatedAt.value;
    localDirty.value = false;
  } else if (action === 'merge') {
    applyMergedBackup(backup);
    cloudUpdatedAt.value = pendingCloudUpdatedAt.value;
    localDirty.value = false;
  }
  pendingCloudBackup.value = null;
  pendingCloudUpdatedAt.value = '';
}

async function loadFromCloud(): Promise<void> {
  try {
    const { data } = await http.get<UserSettingResponse>(
      `/user-settings/${CLOUD_SETTING_KEY}`,
    );
    const backup = data.value as ProfileBackup;
    if (localDirty.value) {
      pendingCloudBackup.value = backup;
      pendingCloudUpdatedAt.value = data.updated_at;
      if (conflictPolicy.value === 'ask') {
        return;
      }
      resolveCloudConflict(conflictPolicy.value);
      return;
    }
    applyBackup(backup);
    cloudUpdatedAt.value = data.updated_at;
    localDirty.value = false;
  } catch {
    error.value = '云端加载失败';
  }
}

function applyTheme(nextTheme: ChartTheme): void {
  theme.value = nextTheme;
  saveConfig();
  renderChart();
}

function onThemeChange(event: Event): void {
  applyTheme((event.target as HTMLSelectElement).value as ChartTheme);
}

function loadProfiles(): void {
  try {
    const raw = window.localStorage.getItem(PROFILES_KEY);
    if (!raw) {
      return;
    }
    profiles.value = JSON.parse(raw) as IndicatorProfile[];
  } catch {
    window.localStorage.removeItem(PROFILES_KEY);
  }
}

function persistProfiles(): void {
  window.localStorage.setItem(PROFILES_KEY, JSON.stringify(profiles.value));
}

function loadConflictHistory(): void {
  try {
    const raw = window.localStorage.getItem(CONFLICT_HISTORY_KEY);
    if (raw) {
      conflictHistory.value = JSON.parse(raw) as ConflictRecord[];
    }
  } catch {
    window.localStorage.removeItem(CONFLICT_HISTORY_KEY);
  }
}

function persistConflictHistory(): void {
  applyConflictCleanup();
  window.localStorage.setItem(CONFLICT_HISTORY_KEY, JSON.stringify(conflictHistory.value));
}

function applyConflictCleanup(): void {
  if (conflictCleanupPolicy.value === 'none') {
    return;
  }
  if (conflictHistory.value.length <= conflictHistoryLimit.value) {
    return;
  }
  if (conflictCleanupPolicy.value === 'archive') {
    const overflow = conflictHistory.value.slice(conflictHistoryLimit.value);
    archivedConflictHistory.value = [...overflow, ...archivedConflictHistory.value];
    persistArchivedConflictHistory();
  }
  conflictHistory.value = conflictHistory.value.slice(0, conflictHistoryLimit.value);
}

function loadCleanupSettings(): void {
  try {
    const raw = window.localStorage.getItem(CLEANUP_SETTINGS_KEY);
    if (!raw) {
      return;
    }
    const parsed = JSON.parse(raw) as {
      policy?: 'none' | 'trim' | 'archive';
      limit?: number;
      archivePolicy?: 'none' | 'trim';
      archiveLimit?: number;
    };
    if (parsed.policy === 'none' || parsed.policy === 'trim' || parsed.policy === 'archive') {
      conflictCleanupPolicy.value = parsed.policy;
    }
    if (typeof parsed.limit === 'number' && parsed.limit > 0) {
      conflictHistoryLimit.value = parsed.limit;
    }
    if (parsed.archivePolicy === 'none' || parsed.archivePolicy === 'trim') {
      archiveCleanupPolicy.value = parsed.archivePolicy;
    }
    if (typeof parsed.archiveLimit === 'number' && parsed.archiveLimit > 0) {
      archiveHistoryLimit.value = parsed.archiveLimit;
    }
  } catch {
    window.localStorage.removeItem(CLEANUP_SETTINGS_KEY);
  }
}

function saveCleanupSettings(): void {
  window.localStorage.setItem(
    CLEANUP_SETTINGS_KEY,
    JSON.stringify({
      policy: conflictCleanupPolicy.value,
      limit: conflictHistoryLimit.value,
      archivePolicy: archiveCleanupPolicy.value,
      archiveLimit: archiveHistoryLimit.value,
    }),
  );
  applyConflictCleanup();
  persistConflictHistory();
  persistArchivedConflictHistory();
}

function clearConflictHistory(): void {
  conflictHistory.value = [];
  persistConflictHistory();
}

function exportConflictHistory(): void {
  const blob = new Blob([JSON.stringify(conflictHistory.value, null, 2)], {
    type: 'application/json',
  });
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'stock-research-conflict-history.json';
  anchor.click();
  window.URL.revokeObjectURL(url);
}

function loadArchivedConflictHistory(): void {
  try {
    const raw = window.localStorage.getItem(CONFLICT_ARCHIVE_KEY);
    if (raw) {
      archivedConflictHistory.value = JSON.parse(raw) as ConflictRecord[];
    }
  } catch {
    window.localStorage.removeItem(CONFLICT_ARCHIVE_KEY);
  }
}

function persistArchivedConflictHistory(): void {
  if (archiveCleanupPolicy.value === 'trim') {
    archivedConflictHistory.value = archivedConflictHistory.value.slice(
      0,
      archiveHistoryLimit.value,
    );
  }
  window.localStorage.setItem(
    CONFLICT_ARCHIVE_KEY,
    JSON.stringify(archivedConflictHistory.value),
  );
}

function archiveConflictHistory(): void {
  archivedConflictHistory.value = [
    ...conflictHistory.value,
    ...archivedConflictHistory.value,
  ];
  conflictHistory.value = [];
  persistConflictHistory();
  persistArchivedConflictHistory();
}

function clearArchivedConflictHistory(): void {
  archivedConflictHistory.value = [];
  persistArchivedConflictHistory();
}

function importConflictHistory(event: Event): void {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) {
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const parsed = JSON.parse(String(reader.result)) as ConflictRecord[];
      if (Array.isArray(parsed)) {
        conflictHistory.value = [...parsed, ...conflictHistory.value];
        persistConflictHistory();
      }
    } catch {
      error.value = '冲突历史导入失败';
    } finally {
      input.value = '';
    }
  };
  reader.readAsText(file);
}

function conflictActionLabel(action: ConflictRecord['action']): string {
  if (action === 'local') return '保留本地';
  if (action === 'cloud') return '使用云端';
  return '合并方案';
}

function saveCurrentProfile(): void {
  const name = profileName.value.trim();
  if (!name) {
    return;
  }
  const config = buildConfigObject();
  const existing = profiles.value.find((profile) => profile.name === name);
  if (existing) {
    existing.config = config;
  } else {
    profiles.value.push({ name, config });
  }
  persistProfiles();
  profileName.value = '';
}

function loadProfile(name: string): void {
  const profile = profiles.value.find((item) => item.name === name);
  if (!profile) {
    return;
  }
  applyConfigObject(profile.config);
  saveConfig();
  void refreshAll();
}

function deleteProfile(name: string): void {
  profiles.value = profiles.value.filter((profile) => profile.name !== name);
  if (defaultProfileName.value === name) {
    defaultProfileName.value = '';
    persistDefaultProfileName();
  }
  persistProfiles();
}

function renameProfile(name: string): void {
  const profile = profiles.value.find((item) => item.name === name);
  if (!profile) {
    return;
  }
  const nextName = window.prompt('新的方案名称', name)?.trim();
  if (!nextName || nextName === name) {
    return;
  }
  if (profiles.value.some((item) => item.name === nextName)) {
    error.value = '方案名称已存在';
    return;
  }
  profile.name = nextName;
  if (defaultProfileName.value === name) {
    defaultProfileName.value = nextName;
    persistDefaultProfileName();
  }
  persistProfiles();
}

function setDefaultProfile(name: string): void {
  if (!profiles.value.some((profile) => profile.name === name)) {
    return;
  }
  defaultProfileName.value = name;
  persistDefaultProfileName();
}

function loadDefaultProfileName(): void {
  defaultProfileName.value = window.localStorage.getItem(DEFAULT_PROFILE_KEY) ?? '';
}

function persistDefaultProfileName(): void {
  if (defaultProfileName.value) {
    window.localStorage.setItem(DEFAULT_PROFILE_KEY, defaultProfileName.value);
  } else {
    window.localStorage.removeItem(DEFAULT_PROFILE_KEY);
  }
}

function applyGroupVisibility(): void {
  saveConfig();
  if (!chart) {
    return;
  }
  const groups: Record<string, string[]> = {
    ma: ['MA5', 'MA10', 'MA20'],
    ema: ['EMA5', 'EMA10', 'EMA20'],
    volumeMa: ['VOL MA5', 'VOL MA10'],
    macd: ['DIF', 'DEA', 'MACD'],
    rsi: ['RSI'],
  };
  const state: Record<string, boolean> = {
    ma: showMa.value,
    ema: showEma.value,
    volumeMa: showVolumeMa.value,
    macd: showMacd.value,
    rsi: showRsi.value,
  };

  for (const [group, names] of Object.entries(groups)) {
    for (const name of names) {
      chart.dispatchAction({
        type: state[group] ? 'legendSelect' : 'legendUnSelect',
        name,
      });
    }
  }
}

function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return '--';
  }
  return value.toLocaleString('zh-CN', { maximumFractionDigits: 4 });
}

function formatTime(value: string | null | undefined): string {
  if (!value) {
    return '--';
  }
  return new Date(value).toLocaleString('zh-CN');
}

function snapshotNumber(snapshot: MarketSnapshot, key: string): number | null {
  const value = snapshot.payload[key];
  return typeof value === 'number' ? value : null;
}

function renderChart(): void {
  if (!chartRef.value) {
    return;
  }
  if (!chart) {
    chart = echarts.init(chartRef.value);
  }

  const times = bars.value.map((bar) => formatTime(bar.time));
  const candleData = bars.value.map((bar) => [bar.open, bar.close, bar.low, bar.high]);
  const volumeData = bars.value.map((bar) => bar.volume ?? 0);
  const ma5 = indicators.value.map((item) => item.ma5);
  const ma10 = indicators.value.map((item) => item.ma10);
  const ma20 = indicators.value.map((item) => item.ma20);
  const ema5 = indicators.value.map((item) => item.ema5);
  const ema10 = indicators.value.map((item) => item.ema10);
  const ema20 = indicators.value.map((item) => item.ema20);
  const volumeMa5 = indicators.value.map((item) => item.volume_ma5);
  const volumeMa10 = indicators.value.map((item) => item.volume_ma10);
  const macdDif = indicators.value.map((item) => item.macd_dif);
  const macdDea = indicators.value.map((item) => item.macd_dea);
  const macdHist = indicators.value.map((item) => item.macd_hist);
  const rsi = indicators.value.map((item) => item.rsi);

  chart.setOption({
    title: { text: `${selectedSymbol.value} K线`, left: 'center' },
    backgroundColor: currentThemeColors().background,
    textStyle: { color: currentThemeColors().text },
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: {
      data: [
        'K线', 'MA5', 'MA10', 'MA20', 'EMA5', 'EMA10', 'EMA20',
        '成交量', 'VOL MA5', 'VOL MA10', 'DIF', 'DEA', 'RSI',
      ],
      top: 28,
    },
    grid: [
      { left: '8%', right: '3%', top: 70, height: 210 },
      { left: '8%', right: '3%', top: 315, height: 50 },
      { left: '8%', right: '3%', top: 405, height: 70 },
      { left: '8%', right: '3%', top: 515, height: 60 },
    ],
    xAxis: [
      { type: 'category', data: times, boundaryGap: true },
      { type: 'category', gridIndex: 1, data: times, boundaryGap: true },
      { type: 'category', gridIndex: 2, data: times, boundaryGap: true },
      { type: 'category', gridIndex: 3, data: times, boundaryGap: true },
    ],
    yAxis: [
      { type: 'value', scale: true },
      { type: 'value', gridIndex: 1, scale: true },
      { type: 'value', gridIndex: 2, scale: true },
      { type: 'value', gridIndex: 3, min: 0, max: 100 },
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1, 2, 3], start: 0, end: 100 },
      { type: 'slider', xAxisIndex: [0, 1, 2, 3], top: 600, start: 0, end: 100 },
    ],
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        data: candleData,
      },
      { name: 'MA5', type: 'line', data: ma5, showSymbol: false },
      { name: 'MA10', type: 'line', data: ma10, showSymbol: false },
      { name: 'MA20', type: 'line', data: ma20, showSymbol: false },
      { name: 'EMA5', type: 'line', data: ema5, showSymbol: false },
      { name: 'EMA10', type: 'line', data: ema10, showSymbol: false },
      { name: 'EMA20', type: 'line', data: ema20, showSymbol: false },
      {
        name: '成交量',
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: volumeData,
      },
      {
        name: 'VOL MA5',
        type: 'line',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: volumeMa5,
        showSymbol: false,
      },
      {
        name: 'VOL MA10',
        type: 'line',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: volumeMa10,
        showSymbol: false,
      },
      {
        name: 'DIF',
        type: 'line',
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: macdDif,
        showSymbol: false,
      },
      {
        name: 'DEA',
        type: 'line',
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: macdDea,
        showSymbol: false,
      },
      {
        name: 'MACD',
        type: 'bar',
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: macdHist,
      },
      {
        name: 'RSI',
        type: 'line',
        xAxisIndex: 3,
        yAxisIndex: 3,
        data: rsi,
        showSymbol: false,
      },
    ],
  });
  applyGroupVisibility();
}

onMounted(() => {
  loadProfiles();
  loadCleanupSettings();
  loadConflictHistory();
  loadArchivedConflictHistory();
  loadDefaultProfileName();
  if (defaultProfileName.value) {
    loadProfile(defaultProfileName.value);
  } else {
    loadConfig();
    void refreshAll();
  }
  refreshTimer = window.setInterval(() => {
    void refreshAll();
  }, 5000);
});

onBeforeUnmount(() => {
  if (refreshTimer !== undefined) {
    window.clearInterval(refreshTimer);
  }
  chart?.dispose();
  chart = null;
});
</script>

<template>
  <section class="market-view">
    <div class="market-toolbar">
      <h1>多标的行情监控</h1>
      <form class="market-form" @submit.prevent="addSymbols">
        <input
          v-model="symbolInput"
          type="text"
          placeholder="例如 600519.SH, 000001.SZ"
        />
        <button type="submit" :disabled="loading">添加</button>
      </form>
    </div>

    <p v-if="error" class="error">
      {{ error }}
    </p>
    <p v-else-if="status === 'loading'" class="status">
      正在刷新行情…
    </p>

    <div class="monitor-grid">
      <button
        v-for="symbol in symbols"
        :key="symbol"
        type="button"
        class="monitor-card"
        :class="{ active: symbol === selectedSymbol }"
        @click="selectSymbol(symbol)"
      >
        <span class="remove" @click.stop="removeSymbol(symbol)">×</span>
        <strong>{{ symbol }}</strong>
        <span>{{ formatNumber(summaries[symbol]?.last_price) }}</span>
        <span>{{ formatNumber(summaries[symbol]?.change_pct) }}%</span>
      </button>
    </div>

    <div v-if="selectedSymbol && summaries[selectedSymbol]" class="summary-grid">
      <div>
        <span>最新价</span>
        <strong>{{ formatNumber(summaries[selectedSymbol].last_price) }}</strong>
      </div>
      <div>
        <span>涨跌额</span>
        <strong>{{ formatNumber(summaries[selectedSymbol].change) }}</strong>
      </div>
      <div>
        <span>涨跌幅</span>
        <strong>{{ formatNumber(summaries[selectedSymbol].change_pct) }}%</strong>
      </div>
      <div>
        <span>买卖价差</span>
        <strong>{{ formatNumber(summaries[selectedSymbol].bid_ask_spread) }}</strong>
      </div>
      <div>
        <span>快照时间</span>
        <strong>{{ formatTime(summaries[selectedSymbol].event_time) }}</strong>
      </div>
    </div>

    <div class="section-toolbar">
      <h2>{{ selectedSymbol || '请选择标的' }} K线</h2>
      <div class="period-selector">
        <button
          v-for="item in ['1m', '5m', '15m', '30m', '1h', '1d']"
          :key="item"
          type="button"
          :class="{ active: period === item }"
          @click="setPeriod(item)"
        >
          {{ item }}
        </button>
      </div>
    </div>
    <div class="indicator-config">
      <label>
        RSI
        <input v-model.number="rsiPeriod" type="number" min="2" max="100" />
      </label>
      <label>
        MACD 快线
        <input v-model.number="macdFast" type="number" min="2" max="100" />
      </label>
      <label>
        MACD 慢线
        <input v-model.number="macdSlow" type="number" min="2" max="200" />
      </label>
      <label>
        MACD 信号
        <input v-model.number="macdSignal" type="number" min="2" max="100" />
      </label>
      <button type="button" @click="applyIndicatorConfig">应用指标参数</button>
    </div>
    <div class="indicator-toggles">
      <span>参数模板：</span>
      <button type="button" @click="applyPreset('default')">默认</button>
      <button type="button" @click="applyPreset('short')">短线</button>
      <button type="button" @click="applyPreset('long')">长线</button>
      <button type="button" @click="applyPreset('ultraShort')">超短</button>
      <button type="button" @click="applyPreset('swing')">波段</button>
      <button type="button" @click="applyPreset('trend')">趋势</button>
      <label><input v-model="showMa" type="checkbox" @change="applyGroupVisibility" /> MA</label>
      <label><input v-model="showEma" type="checkbox" @change="applyGroupVisibility" /> EMA</label>
      <label><input v-model="showVolumeMa" type="checkbox" @change="applyGroupVisibility" /> 均量线</label>
      <label><input v-model="showMacd" type="checkbox" @change="applyGroupVisibility" /> MACD</label>
      <label><input v-model="showRsi" type="checkbox" @change="applyGroupVisibility" /> RSI</label>
    </div>
    <div class="config-actions">
      <button type="button" @click="exportConfig">导出配置</button>
      <button type="button" @click="exportProfilesBackup">备份方案</button>
      <button type="button" @click="syncToCloud">同步到云端</button>
      <button type="button" @click="loadFromCloud">从云端加载</button>
      <label class="import-label">
        导入配置
        <input type="file" accept="application/json" @change="importConfig" />
      </label>
      <label class="import-label">
        导入备份
        <input type="file" accept="application/json" @change="importProfilesBackup" />
      </label>
      <label class="theme-select">
        图表主题
        <select :value="theme" @change="onThemeChange">
          <option value="light">浅色</option>
          <option value="dark">深色</option>
          <option value="cool">冷色</option>
          <option value="warm">暖色</option>
          <option value="contrast">高对比</option>
          <option value="custom">自定义</option>
        </select>
      </label>
      <label class="theme-select">
        冲突策略
        <select v-model="conflictPolicy" @change="saveConfig">
          <option value="ask">每次询问</option>
          <option value="local">自动保留本地</option>
          <option value="cloud">自动使用云端</option>
          <option value="merge">自动合并方案</option>
        </select>
      </label>
      <template v-if="theme === 'custom'">
        <label class="color-field">
          背景色
          <input v-model="customBackground" type="color" @change="applyTheme('custom')" />
        </label>
        <label class="color-field">
          文字色
          <input v-model="customText" type="color" @change="applyTheme('custom')" />
        </label>
      </template>
    </div>
    <div v-if="pendingCloudBackup" class="conflict-panel">
      <span>云端与本地配置存在冲突，请选择处理方式：</span>
      <div v-if="mergePreview" class="merge-preview">
        <span>本地方案保留：{{ mergePreview.localOnly.join(', ') || '无' }}</span>
        <span>云端新增方案：{{ mergePreview.cloudOnly.join(', ') || '无' }}</span>
        <span>同名方案保留本地：{{ mergePreview.conflicting.join(', ') || '无' }}</span>
        <span>默认方案来源：{{ mergePreview.defaultSource }}</span>
      </div>
      <button type="button" @click="resolveCloudConflict('local')">保留本地</button>
      <button type="button" @click="resolveCloudConflict('cloud')">使用云端</button>
      <button type="button" @click="resolveCloudConflict('merge')">合并方案</button>
    </div>
    <div class="profile-manager">
      <div class="profile-save">
        <input v-model="profileName" type="text" placeholder="配置方案名称" />
        <button type="button" @click="saveCurrentProfile">保存当前配置</button>
      </div>
      <div class="profile-list">
        <span v-for="profile in profiles" :key="profile.name" class="profile-item">
          <button type="button" @click="loadProfile(profile.name)">{{ profile.name }}</button>
          <span v-if="defaultProfileName === profile.name" class="default-badge">默认</span>
          <button type="button" @click="renameProfile(profile.name)">重命名</button>
          <button type="button" @click="setDefaultProfile(profile.name)">设为默认</button>
          <button type="button" class="delete" @click="deleteProfile(profile.name)">删除</button>
        </span>
      </div>
    </div>
    <div class="conflict-history">
      <div class="cleanup-settings">
        <label>
          自动清理
          <select v-model="conflictCleanupPolicy" @change="saveCleanupSettings">
            <option value="none">不清理</option>
            <option value="trim">保留最近</option>
            <option value="archive">超限归档</option>
          </select>
        </label>
        <label>
          保留条数
          <input v-model.number="conflictHistoryLimit" type="number" min="1" @change="saveCleanupSettings" />
        </label>
        <label>
          归档清理
          <select v-model="archiveCleanupPolicy" @change="saveCleanupSettings">
            <option value="none">不清理</option>
            <option value="trim">保留最近</option>
          </select>
        </label>
        <label>
          归档保留条数
          <input v-model.number="archiveHistoryLimit" type="number" min="1" @change="saveCleanupSettings" />
        </label>
      </div>
      <div class="history-header">
        <h3>冲突历史</h3>
        <div class="history-actions">
          <button type="button" @click="exportConflictHistory">导出</button>
          <label class="import-label">
            导入
            <input type="file" accept="application/json" @change="importConflictHistory" />
          </label>
          <button type="button" @click="archiveConflictHistory">归档</button>
          <button type="button" @click="clearConflictHistory">清空</button>
        </div>
      </div>
      <p v-if="conflictHistory.length === 0">暂无冲突记录。</p>
      <ul v-else>
        <li v-for="record in conflictHistory" :key="record.id">
          <span>{{ record.time }} · {{ conflictActionLabel(record.action) }}</span>
          <span>本地方案：{{ record.localOnly.join(', ') || '无' }}</span>
          <span>云端新增：{{ record.cloudOnly.join(', ') || '无' }}</span>
          <span>同名保留本地：{{ record.conflicting.join(', ') || '无' }}</span>
          <span>默认来源：{{ record.defaultSource }}</span>
        </li>
      </ul>
      <div v-if="archivedConflictHistory.length > 0" class="archive-summary">
        <span>已归档 {{ archivedConflictHistory.length }} 条</span>
        <button type="button" @click="showArchive = !showArchive">
          {{ showArchive ? '收起归档' : '展开归档' }}
        </button>
        <button type="button" @click="clearArchivedConflictHistory">清空归档</button>
      </div>
      <ul v-if="showArchive">
        <li v-for="record in archivedConflictHistory" :key="record.id">
          <span>{{ record.time }} · {{ conflictActionLabel(record.action) }}</span>
        </li>
      </ul>
    </div>
    <div ref="chartRef" class="chart" />

    <h2>最近快照</h2>
    <table class="snapshot-table">
      <thead>
        <tr>
          <th>时间</th>
          <th>最新价</th>
          <th>昨收</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="snapshot in snapshots" :key="snapshot.event_time">
          <td>{{ formatTime(snapshot.event_time) }}</td>
          <td>{{ formatNumber(snapshotNumber(snapshot, 'lastPrice')) }}</td>
          <td>{{ formatNumber(snapshotNumber(snapshot, 'lastClose')) }}</td>
        </tr>
      </tbody>
    </table>
    <p v-if="!loading && snapshots.length === 0">
      暂无快照数据。
    </p>
  </section>
</template>

<style scoped>
.market-view {
  display: grid;
  gap: 1rem;
}

.market-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.market-form {
  display: flex;
  gap: 0.5rem;
}

.monitor-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
  gap: 0.75rem;
}

.monitor-card {
  position: relative;
  display: grid;
  gap: 0.25rem;
  padding: 0.75rem;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  background: white;
  text-align: left;
  cursor: pointer;
}

.monitor-card.active {
  border-color: #2563eb;
}

.monitor-card .remove {
  position: absolute;
  top: 0.35rem;
  right: 0.45rem;
  color: #9ca3af;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
  gap: 0.75rem;
}

.summary-grid div {
  display: grid;
  gap: 0.25rem;
  padding: 0.75rem;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
}

.summary-grid span {
  color: #6b7280;
  font-size: 0.875rem;
}

.section-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.period-selector {
  display: flex;
  gap: 0.25rem;
}

.period-selector button {
  padding: 0.35rem 0.6rem;
  border: 1px solid #e5e7eb;
  border-radius: 0.35rem;
  background: white;
  cursor: pointer;
}

.period-selector button.active {
  border-color: #2563eb;
  color: #2563eb;
}

.indicator-config {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: end;
}

.indicator-config label {
  display: grid;
  gap: 0.25rem;
  font-size: 0.875rem;
  color: #4b5563;
}

.indicator-config input {
  width: 5rem;
  padding: 0.35rem 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 0.35rem;
}

.indicator-toggles {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  align-items: center;
}

.indicator-toggles label {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.875rem;
  color: #4b5563;
}

.indicator-toggles button {
  padding: 0.35rem 0.6rem;
  border: 1px solid #e5e7eb;
  border-radius: 0.35rem;
  background: white;
  cursor: pointer;
}

.config-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  align-items: center;
}

.config-actions button {
  padding: 0.35rem 0.6rem;
  border: 1px solid #e5e7eb;
  border-radius: 0.35rem;
  background: white;
  cursor: pointer;
}

.theme-select {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.875rem;
  color: #4b5563;
}

.theme-select select {
  padding: 0.35rem 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 0.35rem;
}

.color-field {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.875rem;
  color: #4b5563;
}

.conflict-panel {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
  padding: 0.75rem;
  border: 1px solid #f59e0b;
  border-radius: 0.5rem;
  background: #fffbeb;
  color: #92400e;
}

.conflict-panel button {
  padding: 0.35rem 0.6rem;
  border: 1px solid #f59e0b;
  border-radius: 0.35rem;
  background: white;
  cursor: pointer;
}

.merge-preview {
  display: grid;
  gap: 0.25rem;
  flex-basis: 100%;
  font-size: 0.875rem;
}

.import-label {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.875rem;
  color: #4b5563;
}

.import-label input {
  width: 10rem;
}

.profile-manager {
  display: grid;
  gap: 0.5rem;
}

.profile-save {
  display: flex;
  gap: 0.5rem;
}

.profile-save input {
  padding: 0.35rem 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 0.35rem;
}

.profile-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.profile-item {
  display: inline-flex;
  gap: 0.25rem;
  align-items: center;
  padding: 0.25rem 0.45rem;
  border: 1px solid #e5e7eb;
  border-radius: 0.35rem;
}

.profile-item button {
  border: 0;
  background: transparent;
  cursor: pointer;
}

.profile-item .delete {
  color: #b91c1c;
}

.conflict-history {
  display: grid;
  gap: 0.5rem;
}

.cleanup-settings {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: end;
}

.cleanup-settings label {
  display: grid;
  gap: 0.25rem;
  font-size: 0.875rem;
  color: #4b5563;
}

.cleanup-settings select,
.cleanup-settings input {
  padding: 0.35rem 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 0.35rem;
}

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.history-actions {
  display: flex;
  gap: 0.5rem;
}

.conflict-history ul {
  display: grid;
  gap: 0.5rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.conflict-history li {
  display: grid;
  gap: 0.2rem;
  padding: 0.5rem;
  border: 1px solid #e5e7eb;
  border-radius: 0.4rem;
  font-size: 0.875rem;
}

.archive-summary {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  font-size: 0.875rem;
  color: #6b7280;
}

.default-badge {
  padding: 0.05rem 0.3rem;
  border-radius: 0.3rem;
  background: #dbeafe;
  color: #1d4ed8;
  font-size: 0.75rem;
}

.chart {
  height: 44rem;
}

.snapshot-table {
  width: 100%;
  border-collapse: collapse;
}

.snapshot-table th,
.snapshot-table td {
  padding: 0.5rem;
  border-bottom: 1px solid #e5e7eb;
  text-align: left;
}

.error {
  color: #b91c1c;
}

.status {
  color: #6b7280;
}
</style>
