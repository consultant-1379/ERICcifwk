# Classes for internal and external LDAP auth 

from django_auth_ldap.backend import LDAPBackend

class LDAPBackendInternal(LDAPBackend):
    settings_prefix = "AUTH_LDAP_INTERNAL_"

class LDAPBackendExternal(LDAPBackend):
    settings_prefix = "AUTH_LDAP_EXTERNAL_"
