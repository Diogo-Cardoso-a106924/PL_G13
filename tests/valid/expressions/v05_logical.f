program logicals
  integer a, b
  logical p, q, r

  a = 5
  b = 10

  p = a .eq. b
  p = a .ne. b
  p = a .lt. b
  p = a .le. b
  p = a .gt. b
  p = a .ge. b

  q = .true.
  r = .false.

  p = q .and. r
  p = q .or. r
  p = .not. q
  p = q .eqv. r
  p = q .neqv. r

  p = (a .gt. 0) .and. (b .lt. 20)
  p = (a .eq. 5) .or. (b .eq. 5)
  p = .not. (a .gt. b)
  p = (a .lt. b) .eqv. (b .gt. a)
  p = (a .eq. b) .neqv. .true.
  print *, p
  print *, q, r
end
