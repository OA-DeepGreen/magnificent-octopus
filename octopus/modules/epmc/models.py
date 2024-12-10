from octopus.lib import dataobj
from octopus.lib import xml as xutil
from lxml import etree

class JATSException(Exception):
    def __init__(self, message, rawstring, *args, **kwargs):
        super(JATSException, self).__init__(message, *args, **kwargs)
        self.raw = rawstring

class EPMCFullTextException(JATSException):
    """
    Here for backwards compatibility
    """
    pass

class EPMCMetadataException(Exception):
    def __init__(self, message, rawstring, *args, **kwargs):
        super(EPMCMetadataException, self).__init__(message, *args, **kwargs)
        self.raw = rawstring

class EPMCMetadataXML(object):
    def __init__(self, raw=None, xml=None):
        self.raw = None
        self.xml = None
        if raw is not None:
            self.raw = raw
            try:
                self.xml = etree.fromstring(self.raw)
            except:
                raise JATSException("Unable to parse XML", self.raw)
        elif xml is not None:
            self.xml = xml

    def tostring(self):
        if self.raw is not None:
            return self.raw
        elif self.xml is not None:
            return etree.tostring(self.xml)

    @property
    def title(self):
        # 2018-01-31 TD : adding the default value "no title"
        # 2018-01-30 TD : insert the string(...) to handle html-in-xml cases correctly
        return xutil.xp_first_text(self.xml, "string(title)", default="no title")

    # 2020-02-11 TD : additional bibliographic items as properties
    @property
    def journal(self):
        return xutil.xp_first_text(self.xml, "string(//journalInfo/journal/title)", default="no journal title")

    @property
    def volume(self):
        return xutil.xp_first_text(self.xml, "//journalInfo/volume")

    @property
    def issue(self):
        return xutil.xp_first_text(self.xml, "//journalInfo/issue")

    @property
    def fpage(self):
        pi = xutil.xp_first_text(self.xml, "pageInfo")
        if pi is not None:
            return pi.split('-')[0]
        return pi

    @property
    def lpage(self):
        pi = xutil.xp_first_text(self.xml, "pageInfo")
        if pi is not None and len(pi.split('-')) > 1:
            lp = pi.split('-')[1]
            if len(lp) > 0:
                return lp
        return pi
    # 2020-02-11 TD : end of additional bibliographic items

    @property
    def publication_type(self):
        return xutil.xp_first_text(self.xml, "//pubTypeList/pubType")

    @property
    def language(self):
        return xutil.xp_first_text(self.xml, "language")

    @property
    def publication_date(self):
        pd = xutil.xp_first_text(self.xml, "firstPublicationDate")
        if pd is not None:
            return pd
        pd = xutil.xp_first_text(self.xml, "electronicPublicationDate")
        if pd is not None:
            return pd
        pd = xutil.xp_first_text(self.xml, "//journalInfo/printPublicationDate")
        return pd

    @property
    def pmid(self):
        return xutil.xp_first_text(self.xml, "pmid")

    @property
    def pmcid(self):
        return xutil.xp_first_text(self.xml, "pmcid")

    @property
    def doi(self):
        return xutil.xp_first_text(self.xml, "DOI")

    @property
    def issns(self):
        issn = xutil.xp_first_text(self.xml, "//journalInfo/journal/ISSN")
        essn = xutil.xp_first_text(self.xml, "//journalInfo/journal/ESSN")
        issns = []
        if issn is not None:
            issns.append(issn)
        if essn is not None:
            issns.append(essn)
        return issns

    @property
    def keywords(self):
        return xutil.xp_texts(self.xml, "//keywordList/keyword")

    @property
    def author_string(self):
        return xutil.xp_first_text(self.xml, "//authorString")

    @property
    def authors(self):
        """
        <fullName>Cerasoli E</fullName>
        <firstName>Eleonora</firstName>
        <lastName>Cerasoli</lastName>
        <initials>E</initials>
        <authorId type="ORCID">0000-0000-0000-0000</authorId>
        <affiliation>Biotechnology Department, National Physical Laboratory Teddington, UK.</affiliation>
        """
        author_elements = self.xml.xpath("//authorList/author")
        obs = []
        for ael in author_elements:
            ao = {}

            fn = ael.find("fullName")
            # 2017-06-07 TD : catch if element tag is really empty
            if fn is not None and fn.text is not None:
                ao["fullName"] = fn.text

            first = ael.find("firstName")
            # 2017-06-07 TD : catch if element tag is really empty
            if first is not None and first.text is not None:
                ao["firstName"] = first.text

            last = ael.find("lastName")
            # 2017-06-07 TD : catch if element tag is really empty
            if last is not None and last.text is not None:
                ao["lastName"] = last.text

            inits = ael.find("initials")
            # 2017-06-07 TD : catch if element tag is really empty
            if inits is not None and inits.text is not None:
                ao["initials"] = inits.text

            # 2018-10-17 TD : fetch the author's ORCID if provided
            orcid = ael.find("authorId[@type='ORCID']")
            if orcid is not None and orcid.text is not None:
                ao["orcid"] = orcid.text
            # 2018-10-17 TD

            aff = ael.find("affiliation")
            # 2017-06-07 TD : catch if element tag is really empty
            if aff is not None and aff.text is not None:
                ao["affiliation"] = aff.text

            if len(list(ao.keys())) > 0:
                obs.append(ao)

        return obs

    @property
    def grants(self):
        grant_elements = self.xml.xpath("//grantsList/grant")
        obs = []
        for ael in grant_elements:
            go = {}

            gid = ael.find("grantId")
            if gid is not None:
                go["grantId"] = gid.text

            ag = ael.find("agency")
            if ag is not None:
                go["agency"] = ag.text

            if len(list(go.keys())) > 0:
                obs.append(go)

        return obs

    @property
    def mesh_descriptors(self):
        return xutil.xp_texts(self.xml, "//meshHeadingList/meshHeading/descriptorName")


class EPMCMetadata(dataobj.DataObj):
    def __init__(self, raw):
        super(EPMCMetadata, self).__init__(raw)

    @property
    def pmcid(self):
        return self._get_single("pmcid", self._utf8_unicode(), allow_coerce_failure=False)

    @property
    def pmid(self):
        return self._get_single("pmid", self._utf8_unicode(), allow_coerce_failure=False)

    @property
    def doi(self):
        return self._get_single("doi", self._utf8_unicode(), allow_coerce_failure=False)

    @property
    def in_epmc(self):
        return self._get_single("inEPMC", self._utf8_unicode(), allow_coerce_failure=False)

    @property
    def is_oa(self):
        return self._get_single("isOpenAccess", self._utf8_unicode(), allow_coerce_failure=False)

    @property
    def issn(self):
        return self._get_single("journalInfo.journal.issn", self._utf8_unicode(), allow_coerce_failure=False)

    @property
    def journal(self):
        return self._get_single("journalInfo.journal.title", self._utf8_unicode(), allow_coerce_failure=False)

    # 2020-02-11 TD : additional bibliographic items as properties
    @property
    def volume(self):
        return self._get_single("journalInfo.volume", self._utf8_unicode(), allow_coerce_failure=False)

    @property
    def issue(self):
        return self._get_single("journalInfo.issue", self._utf8_unicode(), allow_coerce_failure=False)

    # 2020-02-11 TD : we have to skip the items 'fpage' and 'lpage' here 
    #                 since there is only an aggregate pageInfo available 
    #                 ... and I don't know how to separate this within the _get_single() setting
    #
    # 2020-02-11 TD : end of additional bibliographic items as properties

    @property
    def essn(self):
        return self._get_single("journalInfo.journal.essn", self._utf8_unicode(), allow_coerce_failure=False)

    @property
    def title(self):
        return self._get_single("title", self._utf8_unicode(), allow_coerce_failure=False)


class JATS(object):
    def __init__(self, raw=None, xml=None):
        self.months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                       "JUL", "AUG", "SEP", "OCT", "NOV", "DEC", "UNA"]
        self.raw = None
        self.xml = None
        if raw is not None:
            self.raw = raw
            try:
                self.xml = etree.fromstring(self.raw)
            except:
                raise JATSException("Unable to parse XML", self.raw)
        elif xml is not None:
            self.xml = xml

    @property
    def title(self):
        # 2018-01-31 TD : adding the default value "no title"
        # 2018-01-30 TD : insert the string(...) to handle html-in-xml cases correctly
        return xutil.xp_first_text(self.xml, "string(//title-group/article-title)", default="no title")

    # 2020-02-11 TD : additional bibliographic items as properties
    @property
    def journal(self):
        return xutil.xp_first_text(self.xml, "string(//journal-title)", default="no journal title")

    @property
    def volume(self):
        return xutil.xp_first_text(self.xml, "//article-meta/volume")

    @property
    def issue(self):
        return xutil.xp_first_text(self.xml, "//article-meta/issue")

    @property
    def fpage(self):
        return xutil.xp_first_text(self.xml, "//article-meta/fpage")

    @property
    def lpage(self):
        return xutil.xp_first_text(self.xml, "//article-meta/lpage")
    # 2020-02-11 TD : end of additional bibliographic items as properties

    @property
    def is_aam(self):
        manuscripts = self.xml.xpath("//article-id[@pub-id-type='manuscript']")
        return len(manuscripts) > 0

    def get_licence_details(self):
        # get the licence type
        l = self.xml.xpath("//license")
        if len(l) > 0:
            l = l[0]
        else:
            return None, None, None
        type = l.get("license-type")
        url = l.get("{http://www.w3.org/1999/xlink}href")
        # get license href for bmj
        if not url:
            url_data = self.xml.xpath("//license/ali:license_ref",namespaces={'ali':'http://www.niso.org/schemas/ali/1.0/'})
            if len(url_data) > 0:
                url = url_data[0].text
        # get the paragraph(s) describing the licence
        para = self.xml.xpath("//license/license-p")
        out = ""
        for p in para:
            out += etree.tostring(p).decode()

        return type, url, out

    @property
    def copyright_statement(self):
        return xutil.xp_first_text(self.xml, "//copyright-statement")

    @property
    def categories(self):
        return xutil.xp_texts(self.xml, "//article-categories/subj-group/subject")

    @property
    def authors(self):
        aels = self.xml.xpath("//contrib-group/contrib[@contrib-type='author']")
        return self._make_contribs(aels)

    @property
    def contribs(self):
        cs = self.xml.xpath("//contrib-group/contrib")
        return self._make_contribs(cs)

    @property
    def emails(self):
        return xutil.xp_texts(self.xml, "//email")

    @property
    def keywords(self):
        return xutil.xp_texts(self.xml, "//kwd-group/kwd")

    @property
    def publisher(self):
        return xutil.xp_first_text(self.xml, "//publisher/publisher-name")

    @property
    def publication_date(self):
        # first look for an explicit publication date
        # 2016-10-17 TD : additionally, use @pub-type attribute:
        #                 look first for epub, second for epub-ppub, third ppub
        pds = self.xml.xpath("//article-meta/pub-date[@pub-type='epub']")
        if len(pds) > 0:
            return self._make_date(pds[0])
        pds = self.xml.xpath("//article-meta/pub-date[@pub-type='epub-ppub']")
        if len(pds) > 0:
            return self._make_date(pds[0])
        pds = self.xml.xpath("//article-meta/pub-date[@pub-type='ppub']")
        if len(pds) > 0:
            return self._make_date(pds[0])
        # 2016-10-17 TD
        # note: @date-type attrib seems to be marked as deprecated... but, so what? 

        pds = self.xml.xpath("//article-meta/pub-date[@date-type='pub']")
        if len(pds) > 0:
            return self._make_date(pds[0])

        # if not, look for exactly one pub-date and use that
        pds = self.xml.xpath("//article-meta/pub-date")
        if len(pds) == 1:
            return self._make_date(pds[0])

        # otherwise, insufficient information
        return None

    @property
    def date_accepted(self):
        das = self.xml.xpath("//history/date[@date-type='accepted']")
        if len(das) > 0:
            return self._make_date(das[0])

    @property
    def date_submitted(self):
        rcs = self.xml.xpath("//history/date[@date-type='received']")
        if len(rcs) > 0:
            return self._make_date(rcs[0])

    @property
    def issn(self):
        return xutil.xp_texts(self.xml, "//journal-meta/issn")

    @property
    def pmcid(self):
        id = xutil.xp_first_text(self.xml, "//article-meta/article-id[@pub-id-type='pmcid']")
        if id is not None and not id.startswith("PMC"):
            id = "PMC" + id
        return id

    @property
    def doi(self):
        return xutil.xp_first_text(self.xml, "//article-meta/article-id[@pub-id-type='doi']")

    def _make_date(self, element):
        ob = xutil.objectify(element)
        year = ob.get("year")
        month = ob.get("month", "01")
        # 2019-01-14 TD : Although it is not compliant with JATS at all, sometimes full month 
        #                 names are used in date fields and, thus, a simple conversion to the 
        #                 corresponding month /number/ helps avoiding silly errors here a lot.  
        #                 Note that 'Unassigned' is also mapped to '01' here.
        if month.upper()[:3] in self.months:
            month = str( 1 + self.months.index(month.upper()[:3]) % 12 )
        day = ob.get("day", "01")
        if len(month) < 2:
            month = "0" + month
        if len(day) < 2:
            day = "0" + day
        if year is None or len(year) != 4:
            return None
        return year + "-" + month + "-" + day

    def _make_contribs(self, elements):
        obs = []

        for c in elements:
            con = {}

            # first see if there is a name we can pull out
            name = c.find("name")
            if name is not None:
                sn = name.find("surname")
                # 2017-06-07 TD : catch if element tag is really empty!
                if sn is not None and sn.text is not None:
                    con["surname"] = sn.text

                gn = name.find("given-names")
                # 2017-06-07 TD : catch if element tag is really empty!
                if gn is not None and gn.text is not None:
                    con["given-names"] = gn.text

            # 2018-10-17 TD : add the contrib-id with @contrib-id-type="orcid"
            # see if there's an ORCID
            orcid = c.find("contrib-id[@contrib-id-type='orcid']")
            if orcid is not None and orcid.text is not None:
                con["orcid"] = orcid.text

            # see if there's an email address
            email = c.find("email")
            # 2017-06-07 TD : catch if element tag is really empty!
            if email is not None and email.text is not None:
                con["email"] = email.text

            # now do the affiliations 
            # 2024-09-30 FG: refactoring, affiliation elements are now found via a separate function,
            # then extracting for each an affiliation string and identifiers.
            affs = []
            for ae in self._find_affiliations(c):

                normalized_affiliation_string = " ".join(_create_aff_string(ae).split())
                affs.append(normalized_affiliation_string)

                # affiliation ids
                aff_ids = ae.findall("institution-wrap/institution-id")
                for aff_id in aff_ids:
                    if aff_id.get("institution-id-type").lower() == "ringgold":
                        val = con.get("ringgold", [])
                        val.append(aff_id.text)
                        con["ringgold"] = val
                    elif aff_id.get("institution-id-type").lower() == "ror":
                        txt = aff_id.text.lower().strip("https://ror.org/")
                        val = con.get("ror", [])
                        val.append(txt)
                        con["ror"] = val
                # affiliation ids for BMJ
                aff_ids = ae.findall("institution")
                for aff_id in aff_ids:
                    r_id = aff_id.get("specific-use")
                    if r_id is not None and r_id != "":
                        r_id = r_id.lower()
                        if r_id.startswith("ringgold_"):
                            val = con.get("ringgold", [])
                            val.append(r_id.strip("ringgold_"))
                            con["ringgold"] = val
                        elif r_id.startswith("ror_"):
                            val = con.get("ror", [])
                            val.append(r_id.strip("ror_"))
                            con["ror"] = val

            if len(affs) > 0:
                con["affiliations"] = affs
            if len(list(con.keys())) > 0:
                obs.append(con)

        return obs

    def _find_affiliations(self, contrib):
        """returns all affiliation elements associated with a specific contributor. avoids duplicate affiliation extraction."""
        aff_elements = []
        # if "aff" is a descendant of contrib
        for aff_el in contrib.findall('aff'):
            aff_elements.append(aff_el)

        # if "aff" is somewhere else in document
        # link 1: linked through xref element
        for xref in contrib.xpath('xref[@ref-type="aff"]'):
            rid = xref.get("rid")
            found = self.xml.xpath("//aff[@id='" + rid + "']")
            if found is not None and found[0] not in aff_elements: 
                aff_elements.append(found[0])

        # link 2: linked via @rid attribute on contrib itself
        if contrib.get("rid") is not None:
            for rid in contrib.get("rid").split():
                found = self.xml.xpath("//aff[@id='" + rid + "']")
                if found is not None and found[0] not in aff_elements: 
                    aff_elements.append(found[0])

        # lastly: affs not directly related to contrib.
        # "global" aff elements that have no identifier
        xp = "//aff[not(@id)]" 
        for aff_el in self.xml.xpath(xp):
            if aff_el not in aff_elements:
                aff_elements.append(aff_el)
                
        # or, if no affiliation at all has been found, take every aff element you can find
        # - as long as the whole file contains three or less affiliations. 
        # this allows us to accomodate jats xml which does not properly link an external affiliation element, 
        # when there is only one affiliation and the connection b/w author and affiliation is obvious to the reader.
        # (the limit is a safeguard for articles with many affiliations, where one contributor may genuinely not have an affiliation.)
        if len(aff_elements) == 0:
            all_affiliations = self.xml.xpath("//aff")
            if len(all_affiliations) < 4:
                for aff_el in all_affiliations:
                    if aff_el not in aff_elements:
                        aff_elements.append(aff_el)
        return aff_elements

    def tostring(self):
        if self.raw is not None:
            return self.raw
        elif self.xml is not None:
            return etree.tostring(self.xml)


#
#
# 2016-11-28 TD : A (new!) class for RSC metadata scheme; according to examples of
#                 <!DOCTYPE article PUBLIC "-//RSC//DTD RSC Primary Article DTD 3.7//EN" 
#                  "http://www.rsc.org/dtds/rscart37.dtd" [...]>
#
class RSCMetadataXML(object):
    def __init__(self, raw=None, xml=None):
        self.months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                       "JUL", "AUG", "SEP", "OCT", "NOV", "DEC", "UNA"]
        self.raw = None
        self.xml = None
        if raw is not None:
            self.raw = raw
            try:
                # 2016-11-30 TD : apparently, RSC XML needs to download some entity defs ...
                #                 FIXME: this could, in principle, be handled locally by the 
                #                 xmlcatalog mechanism... for the time being, let it be as it is.
                parser = etree.XMLParser(load_dtd=True, no_network=False)
                self.xml = etree.fromstring(self.raw, parser)
            except:
                raise JATSException("Unable to parse XML", self.raw)
        elif xml is not None:
            self.xml = xml

    @property
    def title(self):
        # 2018-01-31 TD : adding the default value "no title"
        # 2018-01-30 TD : insert the string(...) to handle html-in-xml cases correctly
        return xutil.xp_first_text(self.xml, "string(//art-front/titlegrp/title)", default="no title")

    # 2020-02-11 TD : additional bibliographic items as properties
    @property
    def journal(self):
        return xutil.xp_first_text(self.xml, "string(//journalref/title[@type='full'])", default="no journal title")

    @property
    def volume(self):
        return xutil.xp_first_text(self.xml, "//published[@type='print']/volumeref/link")

    @property
    def issue(self):
        return xutil.xp_first_text(self.xml, "//published[@type='print']/issueref/link")

    @property
    def fpage(self):
        return xutil.xp_first_text(self.xml, "//published[@type='print']/pubfront/fpage")

    @property
    def lpage(self):
        return xutil.xp_first_text(self.xml, "//published[@type='print']/pubfront/lpage")
    # 2020-02-11 TD : end of additional bibliographic items as properties

    @property
    def is_aam(self):
        # 2016-11-29 TD : FIXME: check if this correctly identifies an 
        #                 "author accepted manuscript"
        manuscripts = self.xml.xpath("//art-admin/date[@role='accepted']")
        return len(manuscripts) <= 0

    def get_licence_details(self):
        # 2016-11-28 TD : apparently, there are no license info provided by RSC...
        return None, None, None
        # # get the licence type
        # l = self.xml.xpath("//license")
        # if len(l) > 0:
        #     l = l[0]
        # else:
        #     return None, None, None
        # type = l.get("license-type")
        # url = l.get("{http://www.w3.org/1999/xlink}href")
        #
        # get the paragraph(s) describing the licence
        # para = self.xml.xpath("//license/license-p")
        # out = ""
        # for p in para:
        #     out += etree.tostring(p)
        #
        # return type, url, out

    @property
    def copyright_statement(self):
        return xutil.xp_first_text(self.xml, "//journalref/cpyrt")

    @property
    def categories(self):
        return xutil.xp_texts(self.xml, "//art-front/subject")

    @property
    def authors(self):
        aels = self.xml.xpath("//art-front/authgrp/author/person")
        return self._make_contribs(aels)

    @property
    def contribs(self):
        cs = self.xml.xpath("//art-front/authgrp/author/person")
        return self._make_contribs(cs)

    @property
    def emails(self):
        return xutil.xp_texts(self.xml, "//email")

    @property
    def keywords(self):
        return xutil.xp_texts(self.xml, "//art-front/keyword")

    @property
    def publisher(self):
        return xutil.xp_first_text(self.xml, "//publisher/orgname/nameelt")

    @property
    def publication_date(self):
        # first look for an explicit publication date
        # 2016-11-28 TD : additionally, use @type attribute:
        #                 look first for web, second for print (and third, subsyear ?!)
        pds = self.xml.xpath("//published[@type='web']/pubfront/date")
        if len(pds) > 0:
            return self._make_date(pds[0])
        pds = self.xml.xpath("//published[@type='print']/pubfront/date")
        if len(pds) > 0:
            return self._make_date(pds[0])
        # 2016-11-28 TD
        # note: @type='subsyear' attrib seems to be obscure... but, so what? 

        pds = self.xml.xpath("//published[@type='subsyear']/pubfront/date")
        if len(pds) > 0:
            return self._make_date(pds[0])

        # if not, look for any pub-date and use the first of it
        pds = self.xml.xpath("//published/pubfront/date")
        if len(pds) > 0:
            return self._make_date(pds[0])

        # otherwise, insufficient information
        return None

    @property
    def date_accepted(self):
        das = self.xml.xpath("//art-admin/date[@role='accepted']")
        if len(das) > 0:
            return self._make_date(das[0])

    @property
    def date_revised(self):
        drs = self.xml.xpath("//art-admin/date[@role='revised']")
        if len(drs) > 0:
            return self._make_date(drs[0])

    @property
    def date_submitted(self):
        rcs = self.xml.xpath("//art-admin/received/date")
        if len(rcs) > 0:
            return self._make_date(rcs[0])

    @property
    def issn(self):
        # 2016-11-28 TD : for all @type values (web, print, and subsyear) there seems
        #                 to be always both the online EISSN and the print ISSN available
        return xutil.xp_texts(self.xml, "//published[@type='web']/journalref/issn")

    @property
    def pmcid(self):
        # 2016-11-28 TD : RSC has no pmcid journals, apparently...
        return None
        # id = xutil.xp_first_text(self.xml, "//article-meta/article-id[@pub-id-type='pmcid']")
        # if id is not None and not id.startswith("PMC"):
        #     id = "PMC" + id
        # return id

    @property
    def doi(self):
        return xutil.xp_first_text(self.xml, "//art-admin/doi")

    def _make_date(self, element):
        ob = xutil.objectify(element)
        year = ob.get("year")
        month = ob.get("month", "01")
        # 2016-11-28 TD : RSC seems to store the full month name and, thus, a simple
        #                 conversion to the month number must be done.  Note that
        #                 'Unassigned' is also mapped to '01' here.
        if month.upper()[:3] in self.months:
            month = str( 1 + self.months.index(month.upper()[:3]) % 12 )
        day = ob.get("day", "01")
        if len(month) < 2:
            month = "0" + month
        if len(day) < 2:
            day = "0" + day
        if year is None or len(year) != 4:
            return None
        return year + "-" + month + "-" + day

    def _make_contribs(self, elements):
        obs = []

        for c in elements:
            con = {}

            # first see if there is a name we can pull out
            name = c.find("persname")
            if name is not None:
                sn = name.find("surname")
                # 2017-06-07 TD : catch if element tag is really empty
                if sn is not None and sn.text is not None:
                    con["surname"] = sn.text

                fn = name.find("fname")
                # 2017-06-07 TD : catch if element tag is really empty
                if fn is not None and fn.text is not None:
                    con["fname"] = fn.text

            # 2018-10-17 TD : fetch the author's ORCID if provided by the rsc xml
            # see if there's an ORCID (as attrib: <person orcid="...">)
            orcid = c.attrib.get("orcid")
            if orcid is not None and orcid != "":
                con["orcid"] = orcid

            # 2016-11-28 TD : note that, with RSC, the email is *always* in the 'aff' tag! 
            # # see if there's an email address
            # email = c.find("email")
            # if email is not None:
            #     con["email"] = email.text

            # now do the affiliations (by 'aff' attribute of parent tag 'author')
            affs = []

            # aff = c.find("aff")
            # if aff is not None:
            #     contents = aff.xpath("string()")
            #     norm = " ".join(contents.split())
            #     affs.append(norm)

            arefs = c.getparent().get("aff")
            if arefs is not None:
                for affid in arefs.split():
                    xp = "//aff[@id='" + affid + "']"
                    aff_elements = self.xml.xpath(xp)
                    for ae in aff_elements:
                        org = ae.xpath("org//text()")
                        adr = ae.xpath("address//text()")
                        norm = ", ".join(org+adr)
                        affs.append(norm)

            # 2016-11-29 TD : there should not be any "global" aff tags with RSC
            # # 2016-11-07 TD : additionally, fetch the "global" affiliation(s) -- start
            # xp = "//aff[not(@id)]"
            # aff_elements = self.xml.xpath(xp)
            # for ae in aff_elements:
            #     contents = ae.xpath("string()")
            #     norm = " ".join(contents.split())
            #     affs.append(norm)
            # # 2016-11-07 TD : "global" affiliation(s) -- end

            if len(affs) > 0:
                con["affiliations"] = affs

            if len(list(con.keys())) > 0:
                obs.append(con)

        return obs

    def tostring(self):
        if self.raw is not None:
            return self.raw
        elif self.xml is not None:
            return etree.tostring(self.xml)


def _create_aff_string(aff_element, string=""):
    """extracts affiliation data as string from aff fields,
    excluding labels and institution-id data.
    recursively iterates through the element's children, 
    adding their text content (as long as they are not sub, sup, label or institution-id elements) 
    and the tail text after the element."""
    if aff_element.text is not None:
        # add element.text. if element has children, 
        # this only selects the element text that comes before the first child element.
        string += " " + aff_element.text
    if len(aff_element) == 0:
            # if no child elements are found, then simply return this string.
            return " ".join(string.split())
    else:
        for child_element in aff_element.iterchildren(): 
            # if current element has children, iterate over them
            if child_element.tag not in ["sub", "sup", "label", "institution-id"]:
                # if child is not a label or identifier, call function again to add the text content
                string = _create_aff_string(child_element, string)
            if child_element.tail is not None:
                # adds the text of the current element that appears after the current child_element, 
                # cf. lxml tutorial for info on .text and .tail properties
                string += child_element.tail
        return " ".join(string.split())
