import json
from pathlib import Path
from datetime import datetime

class MigrationState:
    """Gerencia o estado da migração e permite recuperação"""
    def __init__(self, migration_id=None):
        self.state_dir = Path(__file__).parent.parent / "state"
        self.state_dir.mkdir(exist_ok=True)
        self.migration_id = migration_id or datetime.now().strftime('%Y%m%d_%H%M%S')
        self.state_file = self.state_dir / f"migration_{self.migration_id}.json"
        self.data = self._load_state()
    
    def _load_state(self):
        """Carrega o estado do arquivo"""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_state(self, data, step):
        """Salva o estado atual da migração"""
        state = {
            'migration_id': self.migration_id,
            'timestamp': datetime.now().isoformat(),
            'step': step,
            'data': data
        }
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=4)
        self.data = state
    
    def get_incomplete_migrations(self):
        """Retorna lista de migrações incompletas"""
        migrations = []
        for state_file in self.state_dir.glob("migration_*.json"):
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    # Valida se é uma migração incompleta válida
                    if (state.get('step') != 'completed' and 
                        state.get('migration_id') and 
                        state.get('timestamp') and
                        state.get('step')):
                        migrations.append(state)
            except Exception:
                # Remove arquivos corrompidos
                try:
                    state_file.unlink()
                except:
                    pass
                continue
        return sorted(migrations, key=lambda x: x.get('timestamp', ''), reverse=True)
    
    def clear_state(self):
        """Remove o arquivo de estado"""
        if self.state_file.exists():
            self.state_file.unlink()
            self.data = {}
