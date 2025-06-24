class LinconError(Exception):
    """Classe base para exceções do LINCON"""
    pass

class DependencyError(LinconError):
    """Erro quando uma dependência não está disponível"""
    pass

class ConfigurationError(LinconError):
    """Erro de configuração"""
    pass

class ValidationError(LinconError):
    """Erro de validação de dados"""
    pass

class MigrationError(LinconError):
    """Erro durante o processo de migração"""
    pass
