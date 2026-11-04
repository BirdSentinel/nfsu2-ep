// The user's supplied Player save, embedded so every copy starts from the same template.
import template from './complete-save.txt';
import { isProfileName, NAME_MAX, profileInside, withName } from './profile';
import { t } from './i18n';

export function completeSave(name: string): Uint8Array {
  if (!isProfileName(name)) throw Error(t('A profile\'s name is 1 to {n} letters and digits, as in the game.', { n: NAME_MAX }));
  const bytes = Uint8Array.from(atob(template.trim()), c => c.charCodeAt(0));
  const check = profileInside(bytes);
  if ('bad' in check) throw Error(check.bad);
  return withName(bytes, name);
}
